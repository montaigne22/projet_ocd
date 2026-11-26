"""Grossir une copie de la base de démo, pour mesurer les écrans et les actions planifiées à
l'échelle (docs/RAPPORT_DE_CHARGE.md, partie 9). Jamais sur la production : le script refuse une
base sans le module de démo (ocd_live_demo).

    createdb -T ocd_demo ocd_volume
    VOLUME=10 odoo-bin shell -c odoo.conf -d ocd_volume --no-http < tools/charge/volume.py

Ajoute, pour atteindre VOLUME fois la démo : des vendeurs (copies de ceux de la démo, avec leurs
produits), des clients, des commandes du shop confirmées par le vrai parcours (colis découpés par
vendeur ; 70 % livrés, 10 % en route), des lives payés (passés et à venir), des conversations
WhatsApp (300 au moins) et des abonnés (1 000 au moins). Les dates sont réparties sur les 30
derniers jours. Rien ne part : la démo n'a ni compte WhatsApp ni paiement réel.
"""
# ruff: noqa: F821 (env est donné par le shell d'Odoo)
import os
import random
import time
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tools import SQL

FACTOR = int(os.environ.get("VOLUME", "10"))
rand = random.Random(42)
started = time.time()

if not env["ir.module.module"].search_count([("name", "=", "ocd_live_demo"), ("state", "=", "installed")]):
    raise SystemExit("Refusé : cette base n'a pas la démo d'OCD Live (jamais sur la production).")

env = env(context=dict(env.context, tracking_disable=True, mail_notrack=True, mail_create_nolog=True))
Partner = env["res.partner"].sudo()
SaleOrder = env["sale.order"].sudo()
Booking = env["ocd.live.booking"].sudo()
company = env.company
now = fields.Datetime.now()


def say(text):
    print(f"VOLUME {time.time() - started:6.0f} s  {text}", flush=True)


def safely(function, *args):
    try:
        with env.cr.savepoint():
            return function(*args)
    except (UserError, ValidationError, ValueError) as error:
        return error


def past(days=30):
    return now - timedelta(days=rand.random() * days, minutes=rand.randint(0, 600))


# === VENDEURS ET PRODUITS === #
vendors = Partner.search([("ocd_is_vendor", "=", True), ("ocd_vendor_state", "=", "approved")])
products_of = {vendor: env["product.template"].sudo().search([("ocd_vendor_id", "=", vendor.id), ("sale_ok", "=", True)]) for vendor in vendors}
sources = [vendor for vendor in vendors if products_of[vendor]]
new_vendors = Partner
for index in range(len(vendors) * (FACTOR - 1)):
    source = sources[index % len(sources)]
    copy = safely(source.copy, {"name": f"{source.name} {index + 2}", "phone": f"+2376{50000000 + index:08d}", "email": False})
    if isinstance(copy, Exception):
        continue
    copy.write({"ocd_is_vendor": True, "ocd_vendor_state": "approved"})
    new_vendors |= copy
    for template in products_of[source]:
        product = safely(template.copy, {"name": f"{template.name} · {copy.name}", "ocd_vendor_id": copy.id})
        if not isinstance(product, Exception):
            safely(product.write, {"is_published": True, "ocd_review_state": "approved"})
env.cr.commit()
products = env["product.product"].sudo().search([
    ("product_tmpl_id.ocd_vendor_id", "!=", False), ("sale_ok", "=", True), ("is_published", "=", True),
])
say(f"{len(new_vendors)} vendeurs de plus, {len(products)} produits en vente")

# === CLIENTS === #
customers = Partner.search([("ocd_is_vendor", "=", False), ("district_id", "!=", False)], limit=40)
for index in range(200 * (FACTOR - 1)):
    source = customers[index % len(customers)]
    safely(source.copy, {"name": f"Client {index + 1}", "phone": f"+2376{60000000 + index:08d}", "email": False})
env.cr.commit()
customers = Partner.search([("ocd_is_vendor", "=", False), ("district_id", "!=", False)])
say(f"{len(customers)} clients avec une adresse")

# === COMMANDES DU SHOP === #
carrier = env.ref("ocd_live_shop.carrier_ocd", raise_if_not_found=False)
target = SaleOrder.search_count([("state", "=", "sale")]) * FACTOR


def sell():
    customer = rand.choice(customers)
    lines = [Command.create({"product_id": rand.choice(products).id, "product_uom_qty": rand.randint(1, 2)})
             for _line in range(rand.randint(1, 3))]
    order = SaleOrder.create({"partner_id": customer.id, "order_line": lines})
    if carrier and carrier.is_published:
        rate = carrier.rate_shipment(order)
        if rate.get("success"):
            order.set_delivery_line(carrier, rate["price"])
    order.action_confirm()
    when = past()
    env.cr.execute(SQL("UPDATE sale_order SET date_order = %s, create_date = %s WHERE id = %s", when, when, order.id))
    for parcel in order.picking_ids.filtered("ocd_is_parcel"):
        luck = rand.random()
        if luck < 0.7:
            parcel.write({"ocd_stage": "delivered", "ocd_delivered_at": when + timedelta(hours=rand.randint(4, 40))})
        elif luck < 0.8:
            parcel.write({"ocd_stage": "on_the_way"})
    return order


made = 0
while SaleOrder.search_count([("state", "=", "sale")]) < target and made < target:
    made += 1
    safely(sell)
    if made % 200 == 0:
        env.cr.commit()
        say(f"{made} commandes")
env.cr.commit()
say(f"{SaleOrder.search_count([('state', '=', 'sale')])} commandes, "
    f"{env['stock.picking'].search_count([('ocd_is_parcel', '=', True)])} colis")

# === LIVES PAYÉS === #
package = env.ref("ocd_live.product_package_discovery").product_variant_id
target = Booking.search_count([]) * FACTOR
all_vendors = Partner.search([("ocd_is_vendor", "=", True), ("ocd_vendor_state", "=", "approved")])


def live(start, mode):
    vendor = rand.choice(all_vendors)
    order = SaleOrder.create({
        "partner_id": vendor.id, "require_signature": False, "prepayment_percent": 1.0,
        "order_line": [Command.create({"product_id": package.id, "product_uom_qty": 1})],
    })
    order.action_confirm()
    line = order.order_line[:1]
    end = start + timedelta(hours=(company.ocd_slot_hours or 1.5) * package.ocd_slot_count)
    return Booking.create({
        "partner_id": vendor.id, "company_id": company.id, "mode": mode, "start_datetime": start,
        "slot_count": package.ocd_slot_count, "product_id": package.id, "sale_line_id": line.id,
        "credit_id": line.ocd_credit_ids[:1].id, "state": "done" if end <= now else "confirmed",
    })


day = company._ocd_local_today() - timedelta(days=30)
while Booking.search_count([]) < target and day <= company._ocd_local_today() + timedelta(days=14):
    for start in company._ocd_slot_starts(day):
        for mode in ("studio", "remote", "remote"):
            safely(live, start, mode)
    env.cr.commit()
    day += timedelta(days=1)
say(f"{Booking.search_count([])} lives réservés")

# === CONVERSATIONS WHATSAPP === #
Channel = env["discuss.channel"].sudo()
account = env["whatsapp.account"].sudo().search([], limit=1)
contacts = rand.sample(list(customers), min(len(customers), max(300, 30 * FACTOR)))
if account:
    for index, contact in enumerate(contacts):
        number = f"2376{70000000 + index:08d}"
        channel = safely(Channel.create, {
            "name": contact.name, "channel_type": "whatsapp", "whatsapp_number": number,
            "whatsapp_partner_id": contact.id, "whatsapp_account_id": account.id,
        })
        if isinstance(channel, Exception):
            continue
        for turn in range(rand.randint(1, 4)):
            author = contact if turn % 2 == 0 else env.ref("base.partner_admin")
            channel.message_post(body=rand.choice(["Bonjour", "Ma commande ?", "Merci", "Elle part demain."]),
                                 author_id=author.id, message_type="whatsapp_message")
        if index % 100 == 0:
            env.cr.commit()
    env.cr.commit()
say(f"{Channel.search_count([('channel_type', '=', 'whatsapp')])} conversations WhatsApp"
    + ("" if account else " (aucun compte WhatsApp dans la démo : aucune créée)"))

# === ABONNÉS === #
if "ocd.vendor.follower" in env:
    Follower = env["ocd.vendor.follower"].sudo()
    target = max(1000, Follower.search_count([]) * FACTOR)
    index = 0
    while Follower.search_count([]) < target and index < target * 2:
        index += 1
        safely(lambda: Follower._ocd_follow(rand.choice(all_vendors), Follower._ocd_contact(f"+2376{80000000 + index:08d}")))
        if index % 200 == 0:
            env.cr.commit()
    env.cr.commit()
    say(f"{Follower.search_count([])} abonnés")
say("fini")
