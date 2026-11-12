import json
import logging
from datetime import datetime, time, timedelta

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tools import SQL, BinaryBytes
from odoo.tools.misc import file_open

from . import scenario

_logger = logging.getLogger(__name__)

MODULE = "ocd_live_demo"
PARAM_MESSAGES = "ocd_live_demo.message_ids"
PARAM_MOMO = "ocd_live_demo.momo_pending_msg"
PARAM_COD = "ocd_live_demo.cod_published"
PARAM_WHATSAPP = "ocd_live_demo.whatsapp_account_id"
PARAM_OPEN_DATE = "ocd_live_demo.booking_open_date"
MOMO_MESSAGE = (
    "<p>Envoie le montant par Mobile Money au numéro d'OCD : Mixx by Yas 90 00 00 00, "
    "Flooz 99 00 00 00 (numéros d'exemple). Écris la référence ci-dessous dans le message. "
    "L'équipe confirme dès réception.</p>"
)
OPEN_LINKS = ("queued", "to_check", "published")


class OcdLiveDemo:
    """Scenario of the demo (scenario.py): installed once, then kept on the days around today
    by the scheduled action of the demo (keep_current)."""

    def __init__(self, env):
        self.env = env(context=dict(env.context, tracking_disable=True, mail_notrack=True, mail_create_nolog=True))
        self.company = self.env.company
        self.SaleOrder = self.env["sale.order"].sudo().with_company(self.company)
        self.Booking = self.env["ocd.live.booking"].sudo().with_company(self.company)
        self.Listing = self.env["ocd.directory.listing"].sudo().with_company(self.company)
        # The vendors of the directory: {vendor id: (xmlid, live link, shown name, windows)}
        self.links = {}
        for row in scenario.DIRECTORY:
            vendor = self.env.ref(f"{MODULE}.{row[0]}", raise_if_not_found=False)
            if vendor:
                self.links[vendor.id] = row

    def ref(self, name):
        return self.env.ref(f"{MODULE}.{name}")

    def product(self, xmlid):
        return self.env.ref(xmlid).product_variant_id

    def partners(self):
        """The contacts of the demo."""
        return self.env["res.partner"].browse(
            self.env["ir.model.data"].sudo().search([("module", "=", MODULE), ("model", "=", "res.partner")]).mapped("res_id")
        )

    def start(self, day, hour):
        """The start (naive UTC) of the slot of `day` at `hour` (time of the studio), or None
        when the studio has no slot then (closed day, other hours set by the team)."""
        for start in self.company._ocd_slot_starts(day):
            if self.company._ocd_to_local(start).strftime("%H:%M") == hour:
                return start
        return None

    def today(self):
        return self.company._ocd_local_today()

    def sell(self, partner, product, quantity=1):
        order = self.SaleOrder.create({
            "partner_id": partner.id,
            "order_line": [Command.create({"product_id": product.id, "product_uom_qty": quantity})],
        })
        order.action_confirm()
        return order

    def step(self, label, function, *args, **kwargs):
        """A step of the demo: shown at the step it reached when something is not configured
        (e.g. no accounting yet)."""
        try:
            with self.env.cr.savepoint():
                return function(*args, **kwargs)
        except Exception:  # noqa: BLE001
            _logger.warning("OCD Live demo: %s could not reach its demo step", label, exc_info=True)
            return None

    # === INSTALLATION === #

    def run(self):
        last_message = self.last_message()
        self.payment()
        self.open_bookings()
        self.keep_current()
        self.step("the package of two lives", self.package)
        self.step("the photos of the colours", self.colour_photos)
        self.stock()
        self.shop()
        self.step("the WhatsApp conversations", self.whatsapp)
        self.remember_channel_messages(last_message)

    def last_message(self):
        return self.env["mail.message"].sudo().search([], order="id desc", limit=1).id

    def remember_channel_messages(self, since):
        """The messages of the demo in the channel of the lives of the team, removed with it."""
        channel = self.company.ocd_lives_channel_id
        if not channel:
            return
        messages = self.env["mail.message"].sudo().search([
            ("model", "=", "discuss.channel"), ("res_id", "=", channel.id), ("id", ">", since),
        ])
        if messages:
            params = self.env["ir.config_parameter"].sudo()
            known = json.loads(params.get_str(PARAM_MESSAGES) or "[]")
            params.set_str(PARAM_MESSAGES, json.dumps(sorted(set(known) | set(messages.ids))))

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

    def open_bookings(self):
        """The demo shows OCD Live in service, its lives of the last week included: the bookings
        have no opening date. The date set by the team comes back when the demo is uninstalled."""
        params = self.env["ir.config_parameter"].sudo()
        open_date = self.company.ocd_booking_open_date
        first_day = self.today() - timedelta(days=scenario.PAST_DAYS)
        if open_date and open_date > first_day and not params.get_str(PARAM_OPEN_DATE):
            params.set_str(PARAM_OPEN_DATE, json.dumps({"company": self.company.id, "date": fields.Date.to_string(open_date)}))
            self.company.ocd_booking_open_date = False

    def package(self):
        """Brenda bought a package of two lives: one placed from home with her host, one left to
        place."""
        xmlid, product_xmlid, hour, host = scenario.PACKAGE
        vendor = self.ref(xmlid)
        credit = self.sell(vendor, self.product(product_xmlid)).order_line.ocd_credit_ids[:1]
        for offset in range(3, 10):
            start = self.start(self.today() + timedelta(days=offset), hour)
            if start and not self.Booking._ocd_taken_starts([start], scenario.REMOTE, self.company):
                placed = self.Booking._ocd_book_with_credit(credit, start, scenario.REMOTE)
                placed.write({"animatrice_id": self.ref(host).id, "live_url": self.links[vendor.id][1]})
                return placed
        return None

    # === KEPT ON THE DAYS AROUND TODAY === #

    def keep_current(self):
        """Put the scenario on the days around today (installation, then the scheduled action
        of the demo). Each part only adds what is missing: what the team does during a
        presentation (a link refused, a live cancelled or moved) stays as it is."""
        now = fields.Datetime.now()
        self.step("the directory passes", self.keep_passes)
        self.step("the lives of the directory", self.keep_listings, now)
        self.step("the lives of the studio", self.keep_bookings, now)
        self.step("the replays", self.keep_replays, now)
        self.step("the payment to check", self.keep_payment_to_check, now)
        self.step("the waiting list", self.keep_waitlist)
        self.step("the old records of the demo", self.prune, now)

    def keep_passes(self):
        """Every vendor of the directory has its pass. The first ones were bought on different
        days of the last month (some end soon); a pass over is bought again."""
        product = self.product("ocd_live.product_directory_pass")
        Pass = self.env["ocd.directory.pass"].sudo()
        for index, (xmlid, _url, _title, _windows) in enumerate(scenario.DIRECTORY):
            vendor = self.ref(xmlid)
            passes = Pass.search([("partner_id", "=", vendor.id)])
            if passes.filtered(lambda p: p.state in ("scheduled", "active")):
                continue
            order = self.sell(vendor, product)
            if not passes:
                bought = self.today() - timedelta(days=(4 + 7 * index) % 27)
                days = (product.ocd_pass_days or 30) - 1
                order.order_line.ocd_pass_ids.write({
                    "date_start": bought, "date_end": bought + timedelta(days=days), "state": "active",
                })
                order.date_order = datetime.combine(bought, time(9, 15))

    # --- Directory --- #

    def window_rows(self, window):
        """The vendors who go live in `window` (all of them in a window added by the team)."""
        rows = [row for row in scenario.DIRECTORY if window in self.windows_of(row)]
        if rows:
            return rows
        known = self.env["ocd.directory.window"]
        for row in scenario.DIRECTORY:
            known |= self.windows_of(row)
        return [] if window in known else list(scenario.DIRECTORY)

    def windows_of(self, row):
        windows = self.env["ocd.directory.window"]
        for xmlid in row[3]:
            windows |= self.env.ref(xmlid, raise_if_not_found=False) or windows
        return windows

    def waiting_vendor(self, rows, window, start):
        """The vendor whose link waits for the check of the team in this window (another one
        each day), never one of the countries checked first."""
        candidates = [self.ref(row[0]) for row in rows]
        candidates = [vendor for vendor in candidates if vendor.country_id.code not in scenario.CHECKED_FIRST]
        if not candidates:
            return self.env["res.partner"]
        day = self.company._ocd_to_local(start).date()
        return candidates[scenario.number(day, window.id) % len(candidates)]

    def keep_listings(self, now):
        """The lives of the directory: the vendors of the window of the moment go live one
        after the other (one link waits for the team); the vendors of the next window have
        sent their link."""
        Window = self.env["ocd.directory.window"].sudo()
        found = Window._ocd_find(moment=now, company=self.company)
        if not found:
            return
        window, start, end = found
        if start <= now:
            self.window_listings(window, start, end, now)
            following = Window._ocd_find(moment=end, company=self.company)
            if following and following[1] - now <= timedelta(minutes=scenario.SENT_BEFORE_MINUTES):
                self.send_links(*following)
        elif start - now <= timedelta(hours=scenario.SENT_THE_NIGHT_BEFORE_HOURS):
            self.send_links(window, start, end)

    def listing_values(self, row, window, start, end, state):
        vendor = self.ref(row[0])
        return {
            "partner_id": vendor.id,
            "url": row[1],
            "title": row[2],
            "country_id": vendor.country_id.id,
            "category_id": vendor.ocd_category_id.id,
            "window_id": window.id,
            "window_start": start,
            "window_end": end,
            "state": state,
        }

    def send_links(self, window, start, end):
        """The vendors of the coming window sent their link: it waits for the window."""
        for row in self.window_rows(window):
            vendor = self.ref(row[0])
            if self.Listing.search_count([("partner_id", "=", vendor.id), ("window_start", "=", start)]):
                continue  # already sent (and maybe refused by the team)
            if self.Listing.search_count([("partner_id", "=", vendor.id), ("state", "in", OPEN_LINKS)]):
                continue  # live now, or a link sent from its own space
            self.Listing.create(self.listing_values(row, window, start, end, "queued"))

    def window_listings(self, window, start, end, now):
        rows = self.window_rows(window)
        waiting = self.waiting_vendor(rows, window, start)
        checker = self.company.ocd_live_responsible_id or self.env.ref("base.user_admin")
        for index, row in enumerate(rows):
            vendor = self.ref(row[0])
            listing = self.Listing.search([("partner_id", "=", vendor.id), ("window_start", "=", start)], limit=1)
            if not listing:
                if self.Listing.search_count([("partner_id", "=", vendor.id), ("state", "in", OPEN_LINKS)]):
                    continue  # a link sent from its own space
                listing = self.Listing.create(self.listing_values(row, window, start, end, "to_check"))
            if listing.state == "queued":
                listing.state = "to_check"  # the window is open (as the scheduled action does)
            went_live = start + timedelta(
                minutes=scenario.FIRST_LIVE_MINUTES + scenario.BETWEEN_LIVES_MINUTES * index
            )
            if listing.state == "to_check" and listing.url == row[1] and vendor != waiting and went_live <= now:
                listing.write({"state": "published", "checked_at": went_live, "checked_by_id": checker.id})

    # --- Lives of the studio --- #

    def plan(self):
        """The lives of the week on the days around today: (start, vendor, mode, need, host)."""
        today = self.today()
        rows = []
        for offset in range(-scenario.PAST_DAYS, scenario.NEXT_DAYS + 1):
            day = today + timedelta(days=offset)
            for hour, xmlid, mode, need, host in scenario.WEEK.get(day.weekday(), ()):
                start = self.start(day, hour)
                if start:
                    rows.append((start, self.ref(xmlid), mode, need, host))
        return rows

    def keep_bookings(self, now):
        """The lives booked at the studio on the days around today, each paid when it was
        booked. A live of the plan that exists in any state (also cancelled by the team) is
        not made again."""
        rows = self.plan()
        if not rows:
            return
        vendors = self.env["res.partner"].browse({row[1].id for row in rows})
        existing = self.Booking.search([
            ("partner_id", "in", vendors.ids),
            ("start_datetime", ">=", min(row[0] for row in rows)),
            ("start_datetime", "<=", max(row[0] for row in rows)),
        ])
        known = {(booking.partner_id.id, booking.start_datetime) for booking in existing}
        for start, vendor, mode, need, host in rows:
            if (vendor.id, start) not in known:
                self.paid_live(vendor, start, mode, need, host, now)

    def booked_at(self, vendor, start, now):
        """When a live of the plan was booked: 2 to 9 days before it; a live further away was
        booked during the last days (the bookings of a day are spread, as in real life)."""
        seed = scenario.number(vendor.id, start)
        booked = start - timedelta(days=2 + seed % 8, hours=scenario.number(start) % 9)
        if booked <= now:
            return booked
        return now - timedelta(days=seed % 5, hours=seed % 11, minutes=seed % 53)

    def paid_live(self, vendor, start, mode, need, host, now):
        """A live of the plan: its order paid (the package, and the price of the hour), the live
        confirmed, or done with its replay when it is over."""
        package = self.product("ocd_live.product_package_discovery")
        end = start + timedelta(hours=(self.company.ocd_slot_hours or 1.5) * package.ocd_slot_count)
        if mode == scenario.REMOTE and not host and end <= now:
            host = scenario.PAST_HOST
        try:
            with self.env.cr.savepoint():
                order = self.SaleOrder.create({
                    "partner_id": vendor.id,
                    "company_id": self.company.id,
                    "require_signature": False,
                    "prepayment_percent": 1.0,
                    "order_line": [Command.create({"product_id": package.id, "product_uom_qty": 1})],
                })
                line = order.order_line[:1]
                percent = self.env["ocd.live.price.rule"]._ocd_percent(self.company, start, mode, package)
                if percent:
                    order._ocd_add_hour_price_line(start, mode, percent, line.price_unit / max(package.ocd_live_count, 1))
                order.action_confirm()
                booking = self.Booking.create({
                    "partner_id": vendor.id,
                    "company_id": self.company.id,
                    "mode": mode,
                    "start_datetime": start,
                    "slot_count": package.ocd_slot_count,
                    "product_id": package.id,
                    "sale_line_id": line.id,
                    "credit_id": line.ocd_credit_ids[:1].id,
                    "studio_need": need if mode == scenario.STUDIO else "none",
                    "price_percent": percent,
                    "animatrice_id": self.ref(host).id if host else False,
                    "live_url": self.links.get(vendor.id, (None, False))[1],
                    "state": "done" if end <= now else "confirmed",
                })
                booked = self.booked_at(vendor, start, now)
                order.date_order = booked
                self.env.cr.execute(SQL("UPDATE ocd_live_booking SET create_date = %s WHERE id = %s", booked, booking.id))
                booking.invalidate_recordset(["create_date"])
                if end <= now - timedelta(hours=1):
                    self.add_replay(booking)
                return booking
        except ValidationError as error:
            # The hour was taken meanwhile (a live booked during a presentation): kept
            _logger.info("OCD Live demo: live of %s not placed: %s", vendor.name, error)
            return None

    def add_replay(self, booking):
        """The replay of a past live, published, with the products shown on screen."""
        row = self.links.get(booking.partner_id.id)
        if not row:
            return
        day = self.company._ocd_to_local(booking.start_datetime).date()
        booking.write({"replay_url": scenario.replay_url(row[1], day, row[0]), "replay_published": True})
        products = self.env["product.template"].sudo().search([
            ("ocd_vendor_id", "=", booking.partner_id.id),
            ("is_published", "=", True),
            ("ocd_review_state", "=", "approved"),
        ], order="id")
        if not products:
            return
        first = scenario.number(booking.id) % len(products)
        shown = (products[first:] + products[:first])[:len(scenario.MOMENTS)]
        self.env["ocd.live.moment"].sudo().create([
            {
                "booking_id": booking.id,
                "product_tmpl_id": product.id,
                "offset_seconds": seconds + scenario.number(booking.id, product.id) % 45,
            }
            for seconds, product in zip(scenario.MOMENTS, shown)
        ])

    def keep_replays(self, now):
        """The lives of the demo that are over are done; their replay is published an hour
        later, as the team does."""
        vendors = list(self.links)
        self.Booking.search([
            ("partner_id", "in", vendors), ("state", "=", "confirmed"), ("end_datetime", "<=", now),
        ]).action_mark_done()
        lives = self.Booking.search([
            ("partner_id", "in", vendors),
            ("state", "=", "done"),
            ("replay_url", "=", False),
            ("end_datetime", "<=", now - timedelta(hours=1)),
            ("end_datetime", ">", now - timedelta(days=scenario.PAST_DAYS + 1)),
        ])
        for booking in lives:
            self.add_replay(booking)

    def keep_payment_to_check(self, now):
        """A live held while the team checks the Mobile Money payment announced by the vendor
        (a new one when the team confirmed it, or when its hold is over)."""
        xmlid, mode, need, hours = scenario.PAYMENT_TO_CHECK
        vendor = self.ref(xmlid)
        held = self.Booking.search([("partner_id", "=", vendor.id), ("state", "=", "draft"), ("start_datetime", ">", now)])
        if held - held._ocd_expired_holds(now):
            return None
        package = self.product("ocd_live.product_package_discovery")
        for offset in range(2, 9):
            day = self.today() + timedelta(days=offset)
            starts = [start for start in (self.start(day, hour) for hour in hours) if start]
            taken = self.Booking._ocd_taken_starts(starts, mode, self.company)
            for start in starts:
                if start not in taken:
                    last_message = self.last_message()
                    booking = self.Booking._ocd_book_from_website(vendor, package, start, mode, need)
                    booking.live_url = self.links.get(vendor.id, (None, False))[1]
                    self.momo_payment(booking.sale_order_id)
                    reference = scenario.PAYMENT_REFERENCE % f"{day:%d%m}{scenario.number(day) % 1000:03d}"
                    booking.sale_order_id._ocd_announce_payment(reference)
                    self.remember_channel_messages(last_message)
                    return booking
        return None

    def momo_payment(self, order):
        """The vendor chose the Mobile Money checked by the team on the payment page: the payment
        waits for the team (« Payment to check » in the planning)."""
        provider = self.env.ref("ocd_live.payment_provider_momo_team", raise_if_not_found=False)
        if not provider or not provider.active:
            return None
        Transaction = self.env["payment.transaction"].sudo()
        transaction = Transaction.create({
            "provider_id": provider.id,
            "payment_method_id": provider.payment_method_ids[:1].id,
            "amount": order.amount_total,
            "currency_id": order.currency_id.id,
            "partner_id": order.partner_id.id,
            "reference": Transaction._compute_reference(provider.code, prefix=order.name),
            "sale_order_ids": [Command.set(order.ids)],
        }).with_context(payment_safe_write=True)
        transaction._set_pending()
        return transaction

    def keep_waitlist(self):
        """The full day of the week (Saturday): vendors wait for a free hour."""
        today = self.today()
        day = next(
            (today + timedelta(days=offset) for offset in range(1, 8)
             if (today + timedelta(days=offset)).weekday() == scenario.FULL_DAY),
            None,
        )
        Waitlist = self.env["ocd.live.waitlist"].sudo().with_company(self.company)
        for xmlid, mode in scenario.WAITLIST:
            free = self.Booking._ocd_get_free_counts([day], company=self.company, mode=mode)[day]
            vendor = self.ref(xmlid)
            if not free and not Waitlist.search_count([("partner_id", "=", vendor.id), ("day", "=", day)]):
                Waitlist.create({"partner_id": vendor.id, "day": day, "mode": mode})

    def prune(self, now):
        """The demo does not pile up: its ended links and its unpaid lives cancelled more than
        two weeks ago are removed, and its waiting lists of the days gone."""
        partners = self.partners()
        old = now - timedelta(days=scenario.KEEP_LINKS_DAYS)
        self.Listing.search([
            ("partner_id", "in", partners.ids), ("state", "in", ("ended", "refused")), ("window_end", "<", old),
        ]).unlink()
        self.env["ocd.live.waitlist"].sudo().search([
            ("partner_id", "in", partners.ids), ("day", "<", self.today()),
        ]).unlink()
        released = self.Booking.search([
            ("partner_id", "in", partners.ids), ("state", "=", "cancelled"), ("start_datetime", "<", old),
            ("credit_id", "=", False),
        ])
        orders = released.sale_order_id.filtered(lambda order: order.state == "cancel")
        released.unlink()
        orders.unlink()

    # Stock of the products followed in stock: set on the quants without stock moves, so that
    # the uninstallation removes it all ("Only 3 left", "Sold out" on the pages)
    STOCK = {
        "product_wax_dress": {"Bleu": {"S": 5, "M": 3, "L": 0, "XL": 1}, "Rouge": {"S": 4, "M": 2, "L": 0, "XL": 0}},
        "product_wax_shirt": 6,
        "product_wax_pagne": 4,
        "product_black_soap": 0,
    }

    # The photo of a colour shows on the page as soon as the colour is chosen
    COLOUR_PHOTOS = {"product_wax_dress": {"Rouge": "robe_wax_rouge.jpg"}}

    def colour_photos(self):
        for xmlid, photos in self.COLOUR_PHOTOS.items():
            values = self.ref(xmlid).attribute_line_ids.product_template_value_ids
            for name, file_name in photos.items():
                value = values.filtered(lambda v, name=name: v.name == name)[:1]
                if value:
                    with file_open(f"ocd_live_demo/static/img/{file_name}", "rb") as photo:
                        value.ocd_image = BinaryBytes(photo.read(), filename=file_name)

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


    # === WHATSAPP === #

    def whatsapp(self):
        """Conversations of the WhatsApp screen: customers who wait for an answer, a parcel on
        the way (its code hidden from the team), a vendor, a conversation of more than 24
        hours (only a template). On an archived account: nothing is sent to Meta."""
        if "whatsapp.account" not in self.env:
            return
        account = self.env["whatsapp.account"].sudo().create({
            "name": "OCD Live (démo)",
            "phone_number_id": "ocd-demo",
            "waba_id": "ocd-demo",
            "access_token": "ocd-demo",
            "app_secret": "ocd-demo",
            "bot_enabled": False,
            "away_message_enabled": False,
            "resource_calendar_id": False,
            "active": False,
        })
        self.env["ir.config_parameter"].sudo().set_str(PARAM_WHATSAPP, str(account.id))
        self.wa_account = account
        brenda, fatou, awa = self.ref("vendor_brenda"), self.ref("vendor_fatou"), self.ref("vendor_awa")
        estelle, herve, bertrand = self.ref("customer_estelle"), self.ref("customer_herve"), self.ref("customer_bertrand")
        (brenda | fatou | awa | estelle | herve | bertrand).write({"ocd_whatsapp_optin": True})

        def parcel(customer, vendor=None):
            orders = self.SaleOrder.search([("partner_id", "=", customer.id)], order="id")
            parcels = orders.picking_ids.filtered(lambda p: p.ocd_is_parcel and (not vendor or p.ocd_vendor_id == vendor))
            return parcels[:1]

        # Estelle (Akwa): her order of two parcels, a question about the courier
        channel = self.wa_channel(estelle)
        order = self.SaleOrder.search([("partner_id", "=", estelle.id)], order="id", limit=1)
        self.wa_template(channel, 95, "whatsapp_cloud_sale.template_order_confirmed", order)
        self.wa_in(channel, estelle, 12, "Bonjour, le livreur arrive à quelle heure ? Je dois sortir à 16 h.", waiting=True)
        # Hervé (Bonabéri): on the way with Raoul, the code sent
        channel = self.wa_channel(herve)
        self.wa_template(channel, 48, "ocd_live_shop_whatsapp.template_parcel_on_the_way", parcel(herve))
        self.wa_in(channel, herve, 31, "Bonjour, il est où le livreur ? Je suis à la maison.")
        self.wa_out(channel, 27, "Raoul arrive vers 15 h, il vous appelle 10 minutes avant. Gardez bien votre code.")
        self.wa_in(channel, herve, 25, "D'accord, merci !")
        # Bertrand (Bonamoussadi): nobody at home, asks for another time
        channel = self.wa_channel(bertrand)
        self.wa_template(channel, 70, "ocd_live_shop_whatsapp.template_parcel_failed", parcel(bertrand))
        self.wa_in(channel, bertrand, 52, "Pardon, j'étais en réunion. Vous pouvez repasser après 17 h ?", waiting=True)
        self.wa_note(channel, 50, "Raoul peut repasser à 17 h 30 : à confirmer avec le dispatch.")
        # Fatou: her parcel for Estelle
        channel = self.wa_channel(fatou)
        self.wa_template(channel, 130, "ocd_live_shop_whatsapp.template_parcel_to_prepare", parcel(estelle, fatou))
        self.wa_in(channel, fatou, 64, "C'est prêt, je pars à 15 h 30.")
        self.wa_out(channel, 60, "Merci Fatou ! Estelle attend son colis cet après-midi.")
        # Awa (Lomé): her live confirmed three days ago, more than 24 hours: only a template
        channel = self.wa_channel(awa)
        booking = self.env["ocd.live.booking"].sudo().search(
            [("partner_id", "=", awa.id), ("state", "=", "confirmed")], order="start_datetime", limit=1
        )
        self.wa_template(channel, 60 * 72, "ocd_live_whatsapp.template_live_confirmed", booking)
        self.wa_in(channel, awa, 60 * 71, "Merci, je viens avec ma table.")

    def wa_channel(self, partner):
        number = partner._whatsapp_number()
        return self.env["discuss.channel"].sudo()._whatsapp_get_or_create(self.wa_account, number, None, partner)

    def wa_dated(self, channel, message, minutes):
        date = fields.Datetime.now() - timedelta(minutes=minutes)
        message.sudo().write({"date": date})
        channel.sudo().write({"last_interest_dt": max(channel.last_interest_dt or date, date)})
        return date

    def wa_in(self, channel, partner, minutes, text, waiting=False):
        message = channel.with_context(whatsapp_skip_send=True).message_post(
            author_id=partner.id, body=text, message_type="whatsapp_message", subtype_xmlid="mail.mt_comment",
        )
        date = self.wa_dated(channel, message, minutes)
        self.env["whatsapp.message"].sudo().create({
            "account_id": self.wa_account.id, "direction": "incoming", "state": "received", "message_type": "text",
            "body": text, "channel_id": channel.id, "mail_message_id": message.id, "partner_id": partner.id,
            "phone": channel.whatsapp_number, "model": "discuss.channel", "res_id": channel.id,
        })
        values = {"whatsapp_last_inbound_date": date, "whatsapp_waiting_since": date if waiting else False}
        channel.sudo().write(values)

    def wa_out(self, channel, minutes, text):
        team = self.env.ref("base.user_admin")
        message = channel.with_user(team).with_context(whatsapp_skip_send=True).message_post(
            body=text, message_type="whatsapp_message", subtype_xmlid="mail.mt_comment",
        )
        self.wa_dated(channel, message, minutes)
        self.env["whatsapp.message"].sudo().create({
            "account_id": self.wa_account.id, "direction": "outgoing", "state": "read", "message_type": "text",
            "body": text, "channel_id": channel.id, "mail_message_id": message.id,
            "partner_id": channel.whatsapp_partner_id.id, "phone": channel.whatsapp_number,
            "model": "discuss.channel", "res_id": channel.id,
        })
        channel.sudo().write({"whatsapp_waiting_since": False, "whatsapp_state": "open"})

    def wa_note(self, channel, minutes, text):
        team = self.env.ref("base.user_admin")
        channel.with_user(team).execute_command_note(body=text)
        self.wa_dated(channel, channel.message_ids[:1], minutes)

    def wa_template(self, channel, minutes, xmlid, record):
        template = self.env.ref(xmlid, raise_if_not_found=False)
        if not template or not record:
            return
        template = template.sudo()
        values = {
            variable._get_placeholder_key(): template._render(variable.value, record)[record.id]
            for variable in template.variable_ids
        }
        partner = channel.whatsapp_partner_id
        wa_message = self.env["whatsapp.message"].sudo().create({
            "account_id": self.wa_account.id, "template_id": template.id, "direction": "outgoing", "state": "read",
            "message_type": "template", "body": template._fill_body(values), "partner_id": partner.id,
            "phone": channel.whatsapp_number, "model": record._name, "res_id": record.id,
        })
        message = channel._whatsapp_post_outgoing(wa_message)
        self.wa_dated(channel, message, minutes)


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
        # The payments of the demo (a Mobile Money confirmed by the team during a presentation)
        transactions = env["payment.transaction"].sudo().search(domain)
        if "payment_id" in transactions._fields:
            payments = transactions.payment_id
            payments.filtered(lambda payment: payment.state != "draft").action_draft()
            payments.unlink()
        transactions.unlink()
        pickings.filtered(lambda p: p.state == "cancel").unlink()
        orders.filtered(lambda o: o.state == "cancel").unlink()
    # Stock of the demo products (set on the quants, without stock moves)
    template_ids = env["ir.model.data"].sudo().search(
        [("module", "=", MODULE), ("model", "=", "product.template")]
    ).mapped("res_id")
    if template_ids:
        env["stock.quant"].sudo().search([("product_id.product_tmpl_id", "in", template_ids)]).unlink()
    params = env["ir.config_parameter"].sudo()
    account_id = params.get_str(PARAM_WHATSAPP)
    if account_id and "whatsapp.account" in env:
        # The WhatsApp conversations of the demo, on its archived account
        account = env["whatsapp.account"].sudo().with_context(active_test=False).browse(int(account_id)).exists()
        if account:
            env["whatsapp.message"].sudo().search([("account_id", "=", account.id)]).unlink()
            env["discuss.channel"].sudo().search([("whatsapp_account_id", "=", account.id)]).unlink()
            account.unlink()
    if partner_ids and "whatsapp.message" in env:
        # Messages of the demo contacts on another account (none goes out: ocd_live_demo_whatsapp)
        env["whatsapp.message"].sudo().search([("partner_id", "in", partner_ids)]).unlink()
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
    previous = params.search([("key", "=", PARAM_OPEN_DATE)])
    if previous:
        # The demo had opened the bookings from its day: the date set by the team comes back
        saved = json.loads(previous.value or "{}")
        company = env["res.company"].sudo().browse(saved.get("company") or []).exists()
        if company and saved.get("date"):
            company.ocd_booking_open_date = fields.Date.to_date(saved["date"])
    params.search([("key", "in", (PARAM_MESSAGES, PARAM_MOMO, PARAM_COD, PARAM_WHATSAPP, PARAM_OPEN_DATE))]).unlink()
