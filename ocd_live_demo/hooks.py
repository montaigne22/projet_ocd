import json
import logging
from datetime import timedelta

from odoo import Command, fields

_logger = logging.getLogger(__name__)

MODULE = "ocd_live_demo"
PARAM_MESSAGES = "ocd_live_demo.message_ids"
PARAM_MOMO = "ocd_live_demo.momo_pending_msg"
PARAM_COD = "ocd_live_demo.cod_published"
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
        self.stock()
        self.shop()
        channel = self.company.ocd_lives_channel_id
        if channel:
            messages = self.env["mail.message"].sudo().search([
                ("model", "=", "discuss.channel"), ("res_id", "=", channel.id), ("id", ">", last_message),
            ])
            self.env["ir.config_parameter"].sudo().set_str(PARAM_MESSAGES, json.dumps(messages.ids))

    def payment(self):
        """Mobile Money checked by the team, with example numbers; and the payment in cash at the
        door, the way most customers pay, so that an order of the shop can be paid (it is offered
        only when every parcel of the order accepts it)."""
        params = self.env["ir.config_parameter"].sudo()
        provider = self.env.ref("ocd_live.payment_provider_momo_team", raise_if_not_found=False)
        if provider and not provider.active:
            params.set_str(PARAM_MOMO, str(provider.pending_msg or ""))
            provider.write({"active": True, "pending_msg": MOMO_MESSAGE})
        cod = self.env.ref("delivery.payment_provider_cod", raise_if_not_found=False)
        if cod and cod.company_id == self.company and not (cod.active and cod.is_published):
            params.set_str(PARAM_COD, json.dumps({"active": cod.active, "is_published": cod.is_published}))
            cod.write({"active": True, "is_published": True})

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

    # Stock of the products followed in stock: set on the quants without stock moves, so that
    # the uninstallation removes it all ("Only 3 left", "Sold out" on the pages)
    STOCK = {
        "product_wax_dress": {"Bleu": {"S": 5, "M": 3, "L": 0, "XL": 1}, "Rouge": {"S": 4, "M": 2, "L": 0, "XL": 0}},
        "product_wax_shirt": 6,
        "product_wax_pagne": 4,
        "product_black_soap": 0,
    }

    def stock(self):
        warehouse = self.env["stock.warehouse"].sudo().search([("company_id", "=", self.company.id)], limit=1)
        if not warehouse:
            return
        Quant = self.env["stock.quant"].sudo()
        for xmlid, quantities in self.STOCK.items():
            for variant in self.ref(xmlid).product_variant_ids:
                if isinstance(quantities, dict):
                    names = variant.product_template_attribute_value_ids.mapped("name")
                    color = next((n for n in names if n in quantities), None)
                    qty = quantities.get(color, {}).get(next((n for n in names if n in quantities.get(color, {})), ""), 0)
                else:
                    qty = quantities
                if qty:
                    Quant._update_available_quantity(variant, warehouse.lot_stock_id, qty)

    def order(self, partner, lines):
        """A shop order priced with the delivery of OCD Live (one price per parcel), confirmed."""
        order = self.SaleOrder.create({
            "partner_id": partner.id,
            "order_line": [Command.create({"product_id": product.id, "product_uom_qty": qty}) for product, qty in lines],
        })
        carrier = self.env.ref("ocd_live_shop.carrier_ocd", raise_if_not_found=False)
        if carrier and carrier.is_published:
            rate = carrier.rate_shipment(order)
            if rate.get("success"):
                order.set_delivery_line(carrier, rate["price"])
        order.action_confirm()
        return order

    def variant(self, xmlid, *values):
        """The variant of the product `xmlid` with these values (e.g. "Bleu", "M")."""
        variants = self.ref(xmlid).product_variant_ids
        found = variants.filtered(lambda v: set(values) <= set(v.product_template_attribute_value_ids.mapped("name")))
        return found[:1] or variants[:1]

    def deliver(self, parcel, method, days_ago=0, courier=None):
        """Bring a parcel to "delivered" as the apps do, without validating the stock transfer:
        the demo moves no stock, so that it can be uninstalled."""
        if courier and parcel.ocd_delivery_mode != "vendor":
            parcel._ocd_assign_courier(courier)
        if parcel.ocd_stage == "to_prepare":
            parcel.action_ocd_ready()
        if parcel.ocd_delivery_mode != "vendor" and parcel.ocd_stage == "ready":
            parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()
        if parcel.ocd_cod_state == "to_collect":
            parcel._ocd_collect(method, parcel.ocd_courier_id)
        parcel.write({
            "ocd_stage": "delivered",
            "ocd_delivered_at": fields.Datetime.now() - timedelta(days=days_ago, hours=2),
        })
        # The bill of the vendor needs the accounting (a purchase journal): without it, the
        # parcel stays delivered and the payouts are empty
        self.step("the bill of the vendor", parcel._ocd_create_vendor_bills)

    def step(self, label, function, *args, **kwargs):
        """A step of the demo: shown at the step it reached when something is not configured
        (e.g. no accounting yet)."""
        try:
            with self.env.cr.savepoint():
                return function(*args, **kwargs)
        except Exception:  # noqa: BLE001
            _logger.warning("OCD Live demo: %s could not reach its demo step", label, exc_info=True)
            return None

    def shop(self):
        brenda, fatou = self.ref("vendor_brenda"), self.ref("vendor_fatou")
        junior, raoul = self.ref("courier_ekwalla"), self.ref("courier_nyobe")
        dress = self.variant("product_wax_dress", "Bleu", "S")
        shirt = self.product(f"{MODULE}.product_wax_shirt")
        pagne = self.product(f"{MODULE}.product_wax_pagne")
        butter = self.product(f"{MODULE}.product_shea_butter")

        def parcel_of(order, vendor):
            return order.picking_ids.filtered(lambda p: p.ocd_vendor_id == vendor)[:1]

        # Estelle (Akwa): Brenda's parcel is ready to be picked up, Fatou prepares hers
        estelle = self.order(self.ref("customer_estelle"), [(dress, 1), (butter, 2)])
        self.step("the parcel of Estelle", lambda: parcel_of(estelle, brenda).action_ocd_ready())
        # Hervé (Bonabéri): on the way with Raoul, the code sent
        herve = self.order(self.ref("customer_herve"), [(shirt, 1)])

        def on_the_way():
            parcel = herve.picking_ids[:1]
            parcel._ocd_assign_courier(raoul)
            parcel.action_ocd_ready()
            parcel.action_ocd_pick_up()
            parcel.action_ocd_leave()
        self.step("the parcel of Hervé", on_the_way)
        # Sandrine (Makepe): delivered yesterday by Fatou, paid on her phone
        sandrine = self.order(self.ref("customer_sandrine"), [(butter, 2)])
        self.step("the delivered parcel of Sandrine", self.deliver, parcel_of(sandrine, fatou), "online", days_ago=1)
        # Ruth (Akwa): delivered today by Junior, who has the cash for the evening
        ruth = self.order(self.ref("customer_ruth"), [(self.variant("product_wax_dress", "Rouge", "M"), 1)])
        self.step("the delivered parcel of Ruth", self.deliver, parcel_of(ruth, brenda), "cash", courier=junior)
        # Bertrand (Bonamoussadi): nobody at home, the dispatch offers a new time
        bertrand = self.order(self.ref("customer_bertrand"), [(pagne, 1)])

        def problem():
            parcel = parcel_of(bertrand, brenda)
            parcel._ocd_assign_courier(raoul)
            parcel.action_ocd_ready()
            parcel.action_ocd_pick_up()
            parcel.action_ocd_leave()
            parcel._ocd_report_problem("absent")
        self.step("the parcel of Bertrand", problem)
        # Sandrine again: Brenda is late, reminded then the dispatch alerted
        late = self.order(self.ref("customer_sandrine"), [(shirt, 1)])
        now = fields.Datetime.now()
        self.step("the late parcel", lambda: parcel_of(late, brenda).write({
            "ocd_reminded_at": now - timedelta(hours=3), "ocd_escalated_at": now - timedelta(hours=1),
        }))
        # Payouts of the vendors, to check by the team
        self.step("the payouts", lambda: self.env["ocd.payout"].sudo()._ocd_prepare(vendors=brenda | fatou, force=True))


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
        # Payouts and vendor bills of the demo parcels
        payouts = env["ocd.payout"].sudo().search([("vendor_id", "in", partner_ids)])
        payouts.move_ids.write({"ocd_payout_id": False})
        payouts.unlink()
        bills = env["account.move"].sudo().search(domain + [("move_type", "in", ("in_invoice", "in_refund"))])
        bills.filtered(lambda move: move.state == "posted").button_draft()
        bills.with_context(force_delete=True).unlink()
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
    # Stock of the demo products (set on the quants, without stock moves)
    template_ids = env["ir.model.data"].sudo().search(
        [("module", "=", MODULE), ("model", "=", "product.template")]
    ).mapped("res_id")
    if template_ids:
        env["stock.quant"].sudo().search([("product_id.product_tmpl_id", "in", template_ids)]).unlink()
    params = env["ir.config_parameter"].sudo()
    message_ids = json.loads(params.get_str(PARAM_MESSAGES) or "[]")
    env["mail.message"].sudo().browse(message_ids).exists().unlink()
    provider = env.ref("ocd_live.payment_provider_momo_team", raise_if_not_found=False)
    previous = params.search([("key", "=", PARAM_MOMO)])
    if provider and previous:
        # The demo had enabled it: back as before
        provider.write({"active": False, "pending_msg": previous.value or False})
    cod = env.ref("delivery.payment_provider_cod", raise_if_not_found=False)
    previous = params.search([("key", "=", PARAM_COD)])
    if cod and previous:
        # The demo had published the payment in cash at the door: back as before
        cod.write(json.loads(previous.value or "{}") or {"is_published": False})
    params.search([("key", "in", (PARAM_MESSAGES, PARAM_MOMO, PARAM_COD))]).unlink()
