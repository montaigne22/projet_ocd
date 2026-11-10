import json
import logging
from datetime import timedelta

from odoo import Command, fields

_logger = logging.getLogger(__name__)

MODULE = "ocd_live_demo"
PARAM_MESSAGES = "ocd_live_demo.message_ids"
PARAM_MOMO = "ocd_live_demo.momo_pending_msg"
MOMO_MESSAGE = (
    "<p>Envoie le montant par Mobile Money au numéro d'OCD : Mixx by Yas 90 00 00 00, "
    "Flooz 99 00 00 00 (numéros d'exemple). Écris la référence ci-dessous dans le message. "
    "L'équipe confirme dès réception.</p>"
)
LINKS = [
    ("vendor_brenda", "https://www.tiktok.com/@brenda.wax/live", "Brenda Wax"),
    ("vendor_papa", "https://www.tiktok.com/@papa.ndole/live", "Papa Ndolé"),
    ("vendor_fatou", "https://www.tiktok.com/@fatou.karite/live", "Fatou Karité"),
    ("vendor_junior", "https://www.facebook.com/juniorgadgets/live", "Junior Gadgets"),
    ("vendor_mireille", "https://www.tiktok.com/@mireille.couture/live", "Mireille Couture"),
    ("vendor_aminata", "https://www.instagram.com/aminata.deco/live", "Aminata Déco"),
]


class OcdLiveDemo:
    """Scenario of the demo, set from the day of the installation."""

    def __init__(self, env):
        self.env = env(context=dict(env.context, tracking_disable=True, mail_notrack=True, mail_create_nolog=True))
        self.company = self.env.company
        self.SaleOrder = self.env["sale.order"].sudo().with_company(self.company)
        self.Booking = self.env["ocd.live.booking"].sudo().with_company(self.company)

    def ref(self, name):
        return self.env.ref(f"{MODULE}.{name}")

    def product(self, xmlid):
        return self.env.ref(xmlid).product_variant_id

    def start(self, day, hour):
        """Return the start (naive UTC) of the slot of `day` at `hour` (studio time)."""
        for start in self.company._ocd_slot_starts(day):
            if self.company._ocd_to_local(start).strftime("%H:%M") == hour:
                return start
        return self.company._ocd_slot_starts(day)[0]

    def open_day(self, offset):
        """Return the open day of the studio `offset` open days after the first bookable day."""
        today = self.company._ocd_local_today()
        day = max(today + timedelta(days=1), self.company.ocd_booking_open_date or today)
        found = -1
        for _attempt in range(60):
            if self.company._ocd_is_open_day(day):
                found += 1
                if found == offset:
                    return day
            day += timedelta(days=1)
        return day

    def past_open_day(self):
        day = self.company._ocd_local_today() - timedelta(days=1)
        for _attempt in range(14):
            if self.company._ocd_is_open_day(day):
                return day
            day -= timedelta(days=1)
        return day

    def sell(self, partner, product, quantity=1):
        order = self.SaleOrder.create({
            "partner_id": partner.id,
            "order_line": [Command.create({"product_id": product.id, "product_uom_qty": quantity})],
        })
        order.action_confirm()
        return order

    # === SCENARIO === #

    def run(self):
        last_message = self.env["mail.message"].sudo().search([], order="id desc", limit=1).id
        self.payment()
        self.lives()
        self.directory()
        self.shop()
        channel = self.company.ocd_lives_channel_id
        if channel:
            messages = self.env["mail.message"].sudo().search([
                ("model", "=", "discuss.channel"), ("res_id", "=", channel.id), ("id", ">", last_message),
            ])
            self.env["ir.config_parameter"].sudo().set_str(PARAM_MESSAGES, json.dumps(messages.ids))

    def payment(self):
        """Mobile Money checked by the team, with example numbers."""
        provider = self.env.ref("ocd_live.payment_provider_momo_team", raise_if_not_found=False)
        if provider and not provider.active:
            self.env["ir.config_parameter"].sudo().set_str(PARAM_MOMO, str(provider.pending_msg or ""))
            provider.write({"active": True, "pending_msg": MOMO_MESSAGE})

    def lives(self):
        discovery = self.product("ocd_live.product_package_discovery")
        duo = self.product("ocd_live.product_package_duo")
        first, second = self.open_day(0), self.open_day(1)
        # A live at the studio, paid
        paid = self.Booking._ocd_book_from_website(
            self.ref("vendor_awa"), discovery, self.start(first, "10:00"), "studio", "table"
        )
        paid.sale_order_id.action_confirm()
        # A package of two lives: one placed remote with its host, one left to place
        credit = self.sell(self.ref("vendor_brenda"), duo).order_line.ocd_credit_ids
        placed = self.Booking._ocd_book_with_credit(credit, self.start(second, "14:30"), "remote")
        if placed.state == "confirmed":
            placed.animatrice_id = self.ref("host_dzifa")
        # A slot held during the payment
        self.Booking._ocd_book_from_website(
            self.ref("vendor_junior"), discovery, self.start(first, "16:00"), "remote"
        )
        # A full day soon: the waiting list
        self.env["ocd.live.waitlist"].sudo().create({
            "partner_id": self.ref("vendor_mireille").id, "day": first, "mode": "studio",
        })
        # A past live with its replay and the products shown
        past_day = self.past_open_day()
        past = self.Booking.create({
            "partner_id": self.ref("vendor_brenda").id,
            "mode": "studio",
            "start_datetime": self.start(past_day, "19:00"),
            "slot_count": 1,
            "product_id": discovery.id,
            "state": "done",
            "live_url": "https://www.tiktok.com/@brenda.wax/live",
            "replay_url": "https://www.tiktok.com/@brenda.wax/video/7400000000000000001",
            "replay_published": True,
        })
        for offset, xmlid in ((240, "product_wax_dress"), (1260, "product_wax_shirt"), (2580, "product_wax_pagne")):
            self.env["ocd.live.moment"].sudo().create({
                "booking_id": past.id, "product_tmpl_id": self.ref(xmlid).id, "offset_seconds": offset,
            })

    def directory(self):
        pass_product = self.product("ocd_live.product_directory_pass")
        for xmlid, _url, _title in LINKS:
            self.sell(self.ref(xmlid), pass_product)
        found = self.env["ocd.directory.window"].sudo()._ocd_find(company=self.company)
        if not found:
            return
        window, start, end = found
        now = fields.Datetime.now()
        is_open = start <= now
        Listing = self.env["ocd.directory.listing"].sudo().with_company(self.company)
        for index, (xmlid, url, title) in enumerate(LINKS):
            vendor = self.ref(xmlid)
            Listing.create({
                "partner_id": vendor.id,
                "url": url,
                "title": title,
                "country_id": vendor.country_id.id,
                "category_id": vendor.ocd_category_id.id,
                "window_id": window.id,
                "window_start": start,
                "window_end": end,
                "state": "published" if is_open else "queued",
                "checked_at": now - timedelta(minutes=5 + 7 * index) if is_open else False,
            })

    def shop(self):
        dress = self.product(f"{MODULE}.product_wax_dress")
        shirt = self.product(f"{MODULE}.product_wax_shirt")
        butter = self.product(f"{MODULE}.product_shea_butter")
        estelle = self.SaleOrder.create({
            "partner_id": self.ref("customer_estelle").id,
            "order_line": [
                Command.create({"product_id": dress.id, "product_uom_qty": 1}),
                Command.create({"product_id": butter.id, "product_uom_qty": 2}),
            ],
        })
        estelle.action_confirm()
        herve = self.sell(self.ref("customer_herve"), shirt)
        courier = self.ref("courier_ekwalla")
        try:
            # Parcel of Brenda for Estelle: ready to be picked up
            estelle.picking_ids.filtered(lambda p: p.ocd_vendor_id == self.ref("vendor_brenda")).action_ocd_ready()
            # Parcel of Hervé: on the way with the courier
            parcel = herve.picking_ids[:1]
            parcel._ocd_assign_courier(courier)
            parcel.action_ocd_ready()
            parcel.action_ocd_pick_up()
            parcel.action_ocd_leave()
        except Exception:  # noqa: BLE001 - the demo shows the parcels at the steps it reached
            _logger.warning("OCD Live demo: a parcel could not reach its demo step", exc_info=True)


def post_init_hook(env):
    OcdLiveDemo(env).run()


def uninstall_hook(env):
    """Cancel and remove everything the demo created around its contacts; Odoo then removes
    the records of the module (contacts, products, hosts, prices of the hours)."""
    env = env(context=dict(env.context, tracking_disable=True, mail_notrack=True))
    partner_ids = env["ir.model.data"].sudo().search(
        [("module", "=", MODULE), ("model", "=", "res.partner")]
    ).mapped("res_id")
    if partner_ids:
        domain = [("partner_id", "in", partner_ids)]
        orders = env["sale.order"].sudo().with_context(active_test=False).search(domain)
        pickings = orders.picking_ids
        pickings.filtered(lambda p: p.state not in ("done", "cancel")).action_cancel()
        bookings = env["ocd.live.booking"].sudo().search(domain)
        bookings.filtered(lambda b: b.state in ("draft", "confirmed")).action_cancel()
        bookings.filtered(lambda b: b.state == "done").write({"state": "cancelled"})
        orders.filtered(lambda o: o.state != "cancel")._action_cancel()
        bookings.unlink()
        for model in ("ocd.live.credit", "ocd.directory.pass", "ocd.directory.listing", "ocd.live.waitlist", "ocd.directory.alert"):
            env[model].sudo().with_context(active_test=False).search(domain).unlink()
        env["payment.transaction"].sudo().search(domain).filtered(lambda t: t.state in ("draft", "cancel", "error")).unlink()
        pickings.filtered(lambda p: p.state == "cancel").unlink()
        orders.filtered(lambda o: o.state == "cancel").unlink()
    params = env["ir.config_parameter"].sudo()
    message_ids = json.loads(params.get_str(PARAM_MESSAGES) or "[]")
    env["mail.message"].sudo().browse(message_ids).exists().unlink()
    provider = env.ref("ocd_live.payment_provider_momo_team", raise_if_not_found=False)
    previous = params.search([("key", "=", PARAM_MOMO)])
    if provider and previous:
        # The demo had enabled it: back as before
        provider.write({"active": False, "pending_msg": previous.value or False})
    params.search([("key", "in", (PARAM_MESSAGES, PARAM_MOMO))]).unlink()
