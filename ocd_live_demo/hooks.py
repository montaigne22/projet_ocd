import json
import logging
from datetime import datetime, time, timedelta

import pytz

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
        # The messages of the demo (announcements in the channels of the team, alerts of the
        # parcels) are written in the language of the team, also from the scheduled action
        admin = env.ref("base.user_admin", raise_if_not_found=False)
        lang = (admin.lang if admin else False) or env.context.get("lang") or "en_US"
        self.env = env(context=dict(
            env.context, lang=lang, tracking_disable=True, mail_notrack=True, mail_create_nolog=True,
        ))
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
        self.step("the WhatsApp account", self.whatsapp_setup)
        self.step("the photos of the colours", self.colour_photos)
        self.keep_current()
        self.step("the package of two lives", self.package)
        self.step("the conversation of Awa", self.whatsapp_awa)
        self.remember_channel_messages(last_message)

    def last_message(self):
        return self.env["mail.message"].sudo().search([], order="id desc", limit=1).id

    def remember_channel_messages(self, since):
        """The messages of the demo in the channels of the team (lives, deliveries), removed with
        it."""
        channels = self.company.ocd_lives_channel_id
        if "ocd_deliveries_channel_id" in self.company._fields:
            channels |= self.company.ocd_deliveries_channel_id
        if not channels:
            return
        messages = self.env["mail.message"].sudo().search([
            ("model", "=", "discuss.channel"), ("res_id", "in", channels.ids), ("id", ">", since),
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
        last_message = self.last_message()
        self.step("the directory passes", self.keep_passes)
        self.step("the lives of the directory", self.keep_listings, now)
        self.step("the lives of the studio", self.keep_bookings, now)
        self.step("the replays", self.keep_replays, now)
        self.step("the payment to check", self.keep_payment_to_check, now)
        self.step("the waiting list", self.keep_waitlist)
        self.step("the shop in Douala", self.keep_shop, now)
        self.step("the old records of the demo", self.prune, now)
        self.remember_channel_messages(last_message)

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
                    booking = self.Booking._ocd_book_from_website(vendor, package, start, mode, need)
                    booking.live_url = self.links.get(vendor.id, (None, False))[1]
                    self.momo_payment(booking.sale_order_id)
                    reference = scenario.PAYMENT_REFERENCE % f"{day:%d%m}{scenario.number(day) % 1000:03d}"
                    booking.sale_order_id._ocd_announce_payment(reference)
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
        self.env["ocd.live.demo.event"].sudo().search([
            ("create_date", "<", now - timedelta(days=scenario.KEEP_STEPS_DAYS)),
        ]).unlink()

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

    def keep_stock(self):
        """The stock of the products followed in stock stays at its level of the scenario
        (« Only 3 left », sizes sold out): the parcels of the demo move no stock (so that it can
        be removed), the vendors restock what the orders of the demo hold."""
        warehouse = self.env["stock.warehouse"].sudo().search([("company_id", "=", self.company.id)], limit=1)
        if not warehouse:
            return
        location = warehouse.lot_stock_id
        Quant = self.env["stock.quant"].sudo()
        for xmlid, quantities in self.STOCK.items():
            for variant in self.ref(xmlid).product_variant_ids:
                if isinstance(quantities, dict):
                    names = variant.product_template_attribute_value_ids.mapped("name")
                    sizes = quantities.get(next((name for name in names if name in quantities), None), {})
                    target = sizes.get(next((name for name in names if name in sizes), ""), 0)
                else:
                    target = quantities
                quants = Quant.search([("product_id", "=", variant.id), ("location_id", "=", location.id)])
                free = sum(quants.mapped("quantity")) - sum(quants.mapped("reserved_quantity"))
                if target > free:
                    Quant._update_available_quantity(variant, location, target - free)

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

    # === THE SHOP IN DOUALA, KEPT ON THE DAYS AROUND TODAY === #

    def shop_utc(self, local):
        """A moment of Douala (naive) as stored (naive UTC)."""
        return pytz.timezone(scenario.SHOP_TZ).localize(local).astimezone(pytz.utc).replace(tzinfo=None)

    def shop_today(self, now):
        return pytz.utc.localize(now).astimezone(pytz.timezone(scenario.SHOP_TZ)).date()

    def shop_vendors(self):
        """The vendors whose products OCD sells and delivers."""
        return self.partners().filtered(lambda partner: partner.ocd_is_vendor and partner.ocd_sale_mode == "ocd")

    def shop_stories(self, index):
        """The vendors of an order of the day, each with the story of its parcel: the vendors
        who deliver themselves do it the same day, or the next morning for an evening order."""
        hour, _customer, lines, story = scenario.SHOP_DAY[index]
        stories = []
        for product_xmlid, _variants, _quantity in lines:
            vendor = self.ref(product_xmlid).ocd_vendor_id
            if vendor and vendor not in [row[0] for row in stories]:
                if vendor.ocd_delivery_mode == "vendor":
                    stories.append((vendor, "vendor_evening" if hour >= scenario.VENDOR_EVENING_FROM else "vendor"))
                else:
                    stories.append((vendor, story))
        return stories

    def shop_plan(self, now):
        """The steps of the shop on the days kept, in the order of time: (moment, key, function,
        arguments). A step of the next day of an order of today comes when its time comes."""
        today = self.shop_today(now)
        steps = []
        for offset in range(-scenario.SHOP_PAST_DAYS, 1):
            day = today + timedelta(days=offset)

            def at(hour, day=day):
                hours, minutes = (int(part) for part in hour.split(":"))
                return datetime.combine(day, time(hours, minutes))

            for index, (hour, _customer, _lines, _story) in enumerate(scenario.SHOP_DAY):
                ordered = at(hour)
                key = f"shop:{day}:{index}"
                steps.append((ordered, f"{key}:order", self.shop_order, (key, day, index, ordered)))
                stories = self.shop_stories(index)
                for vendor, story in stories:
                    for number, (name, step_time) in enumerate(scenario.STORIES[story]):
                        moment = scenario.when(ordered, step_time)
                        steps.append((moment, f"{key}:{vendor.id}:{number}:{name}", self.shop_parcel_step,
                                      (key, vendor, name, self.shop_utc(moment))))
                delivered = next(
                    (scenario.when(ordered, step_time) for name, step_time in scenario.STORIES[stories[0][1]]
                     if name.startswith("deliver")),
                    ordered,
                ) if stories else ordered
                for number, talk in enumerate(scenario.SHOP_TALKS[index]):
                    moment = scenario.when(ordered, talk[0])
                    steps.append((moment, f"{key}:talk:{number}", self.shop_talk,
                                  (key, talk, self.shop_utc(moment), delivered)))
            steps.append((at(scenario.PAYOUTS_PREPARED), f"shop:{day}:payouts", self.shop_payouts, (day,)))
            steps.append((at(scenario.PAYOUTS_PAID), f"shop:{day}:paid", self.shop_pay, (day,)))
            moment = at(scenario.CASH_HANDOVER)
            steps.append((moment, f"shop:{day}:cash", self.shop_cash, (self.shop_utc(moment),)))
        return sorted(steps, key=lambda step: step[0])

    def keep_shop(self, now):
        """The shop of Douala on the last week and today: the orders of each day, each parcel
        along its story, the conversations on WhatsApp, the cash handed over in the evening, the
        payouts of the vendors. Each step takes place once (ocd.live.demo.event), in the order
        of time, as soon as its time comes."""
        self.keep_stock()
        # First the parcels left open the days before: delivered in the evening of their order,
        # their cash is handed over with the cash of that day
        self.step("the parcels of the former scenario", self.shop_tidy, now)
        Event = self.env["ocd.live.demo.event"].sudo()
        local_now = pytz.utc.localize(now).astimezone(pytz.timezone(scenario.SHOP_TZ)).replace(tzinfo=None)
        steps = [step for step in self.shop_plan(now) if step[0] <= local_now]
        done = set(Event.search([("key", "in", [step[1] for step in steps])]).mapped("key"))
        for _moment, key, function, args in steps:
            if key in done:
                continue
            result = self.step(key, function, *args)
            order = result if getattr(result, "_name", None) == "sale.order" else self.env["sale.order"]
            Event.create({"key": key, "sale_order_id": order.id})
        self.keep_stock()

    def shop_order(self, key, day, index, ordered):
        """An order of the day, placed at its hour (one parcel per vendor)."""
        _hour, customer, lines, _story = scenario.SHOP_DAY[index]
        order_lines = []
        for product_xmlid, variants, quantity in lines:
            if variants:
                product = self.variant(product_xmlid, *variants[scenario.number(day, index) % len(variants)])
            else:
                product = self.product(f"{MODULE}.{product_xmlid}")
            order_lines.append((product, quantity))
        order = self.order(self.ref(customer), order_lines)
        moment = self.shop_utc(ordered)
        order.date_order = moment
        if order.picking_ids:
            # The time to prepare counts from the order (reminders of the vendors)
            self.env.cr.execute(SQL(
                "UPDATE stock_picking SET create_date = %s WHERE id IN %s", moment, tuple(order.picking_ids.ids)
            ))
            order.picking_ids.invalidate_recordset(["create_date"])
        return order

    def shop_order_of(self, key):
        return self.env["ocd.live.demo.event"].sudo().search([("key", "=", f"{key}:order")], limit=1).sale_order_id

    def shop_parcel(self, order, vendor):
        return order.picking_ids.filtered(lambda picking: picking.ocd_is_parcel and picking.ocd_vendor_id == vendor)[:1]

    def shop_parcel_step(self, key, vendor, name, moment):
        parcel = self.shop_parcel(self.shop_order_of(key), vendor)
        if parcel:
            getattr(self, f"parcel_{name}")(parcel, moment)

    # Each step checks where the parcel is: a parcel handled by the team during a presentation
    # (delivered with the code, problem, returned) is left as it is

    def parcel_ready(self, parcel, moment):
        if parcel.ocd_stage == "to_prepare":
            parcel.action_ocd_ready()
            parcel.ocd_ready_at = moment
            parcel.activity_feedback(["ocd_live_shop.mail_activity_type_parcel_late"])

    def parcel_pick_up(self, parcel, moment):
        if parcel.ocd_stage in ("to_prepare", "ready") and parcel.ocd_delivery_mode != "vendor":
            parcel.action_ocd_pick_up()
            parcel.ocd_picked_at = moment

    def parcel_leave(self, parcel, moment):
        if parcel.ocd_stage in ("ready", "picked") and parcel.ocd_courier_id:
            parcel.action_ocd_leave()
            parcel.write({"ocd_left_at": moment, "ocd_code_sent_at": moment})

    def parcel_deliver_cash(self, parcel, moment):
        self.parcel_deliver(parcel, moment, "cash")

    def parcel_deliver_online(self, parcel, moment):
        self.parcel_deliver(parcel, moment, "online")

    def parcel_deliver(self, parcel, moment, method):
        """Delivered with the code of the customer, as the app of the courier does, without
        validating the stock transfer (the demo moves no stock, so that it can be removed)."""
        if parcel.ocd_stage != "on_the_way":
            return
        if parcel.ocd_cod_state == "to_collect":
            collector = parcel.ocd_courier_id
            if method == "cash" and "cash" not in parcel._ocd_allowed_cod_methods(collector):
                method = "online"  # a vendor who does not collect: the customer pays on the phone
            parcel._ocd_collect(method, collector)
            parcel.ocd_cod_collected_at = moment
        parcel.write({"ocd_stage": "delivered", "ocd_delivered_at": moment})
        # The bill of the vendor needs the accounting (a purchase journal): without it, the
        # parcel stays delivered and the payouts are empty
        if self.env["account.journal"].sudo().search_count(
            [("type", "=", "purchase"), ("company_id", "=", parcel.company_id.id)], limit=1
        ):
            self.step("the bill of the vendor", parcel._ocd_create_vendor_bills)

    def parcel_remind(self, parcel, moment):
        parcel._ocd_escalate(moment)

    def parcel_escalate(self, parcel, moment):
        parcel._ocd_escalate(moment)

    def parcel_absent(self, parcel, moment):
        if parcel.ocd_stage in ("ready", "picked", "on_the_way"):
            parcel._ocd_report_problem("absent")

    def parcel_retry(self, parcel, moment):
        if parcel.ocd_stage == "problem":
            parcel.action_ocd_retry()

    def shop_cash(self, moment):
        """The couriers hand over the cash collected until `moment`; the team counts it."""
        Remittance = self.env["ocd.cash.remittance"].sudo()
        Picking = self.env["stock.picking"].sudo()
        for courier in self.partners().filtered("ocd_is_courier"):
            if Picking.search_count([
                ("ocd_cod_collected_by_id", "=", courier.id), ("ocd_cod_state", "=", "collected"),
                ("ocd_cod_method", "=", "cash"), ("ocd_remittance_id", "=", False),
                ("ocd_cod_collected_at", "<=", moment),
            ]):
                remittance = Remittance._ocd_open_for(courier)
                # The cash collected after this evening goes with the next one
                remittance.picking_ids.filtered(
                    lambda parcel: parcel.ocd_cod_collected_at and parcel.ocd_cod_collected_at > moment
                ).write({"ocd_remittance_id": False})
                remittance.write({"amount_received": remittance.amount_expected, "date": moment})
                remittance.action_done()

    def shop_payouts(self, day):
        """The payouts of the day (the vendors of the shop are paid every day)."""
        self.env["ocd.payout"].sudo()._ocd_prepare(vendors=self.shop_vendors(), day=day)

    def shop_pay(self, day):
        """The team paid the payouts of the days before by Mobile Money (the demo records no
        payment in the accounting, so that it can be removed)."""
        payouts = self.env["ocd.payout"].sudo().search([
            ("vendor_id", "in", self.shop_vendors().ids), ("state", "in", ("draft", "validated")), ("date", "<", day),
        ])
        for payout in payouts:
            payout.write({"state": "paid", "payment_reference": scenario.PAYOUT_REFERENCE % f"{payout.date:%d%m}-{payout.id}"})

    def shop_tidy(self, now):
        """The parcels of the demo left open by its former scenario, or by a presentation the
        days before, are delivered in the evening of their order: the dispatch screens show
        the parcels of the days of now."""
        known = self.env["ocd.live.demo.event"].sudo().search([("sale_order_id", "!=", False)]).sale_order_id
        customers = self.partners().filtered(lambda partner: not partner.ocd_is_vendor and not partner.ocd_is_courier)
        parcels = self.env["stock.picking"].sudo().search([
            ("ocd_is_parcel", "=", True), ("partner_id", "in", customers.ids),
            ("ocd_stage", "in", ("to_prepare", "ready", "picked", "on_the_way", "problem")),
            ("sale_id", "not in", known.ids),
            ("create_date", "<", self.shop_utc(datetime.combine(self.shop_today(now), time()))),
        ])
        tz = pytz.timezone(scenario.SHOP_TZ)
        for parcel in parcels:
            ordered = parcel.sale_id.date_order or parcel.create_date
            day = pytz.utc.localize(ordered).astimezone(tz).date()
            moment = max(min(self.shop_utc(datetime.combine(day, time(18, 0))), now), ordered)
            self.parcel_retry(parcel, moment)
            self.parcel_ready(parcel, moment)
            self.parcel_pick_up(parcel, moment)
            if parcel.ocd_stage in ("ready", "picked") and not parcel.ocd_courier_id:
                parcel._ocd_assign_courier(self.env["res.partner"]._ocd_find_courier(parcel.ocd_district_id))
            self.parcel_leave(parcel, moment)
            self.parcel_deliver(parcel, moment, "cash")

    # === WHATSAPP === #

    def whatsapp_account(self):
        """The archived WhatsApp account of the demo (nothing is sent to Meta), or None."""
        if "whatsapp.account" not in self.env:
            return None
        account_id = self.env["ir.config_parameter"].sudo().get_str(PARAM_WHATSAPP)
        if not account_id or not account_id.isdigit():
            return None
        return self.env["whatsapp.account"].sudo().with_context(active_test=False).browse(int(account_id)).exists() or None

    def whatsapp_setup(self):
        """The WhatsApp account of the demo, archived: the conversations of the WhatsApp screen
        are on it, and nothing is sent to Meta."""
        if "whatsapp.account" not in self.env or self.whatsapp_account():
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
        talking = self.partners().filtered(lambda partner: not partner.ocd_is_courier and partner.phone)
        talking.write({"ocd_whatsapp_optin": True})

    def whatsapp_awa(self):
        """Awa (Lomé): her live confirmed three days ago, more than 24 hours: only a template
        can be sent to her now."""
        account = self.whatsapp_account()
        if not account:
            return
        awa = self.ref("vendor_awa")
        booking = self.Booking.search([("partner_id", "=", awa.id), ("state", "=", "confirmed")], order="start_datetime", limit=1)
        channel = self.wa_channel(account, awa)
        now = fields.Datetime.now()
        self.wa_template(account, channel, now - timedelta(hours=72), "ocd_live_whatsapp.template_live_confirmed", booking)
        self.wa_in(account, channel, awa, now - timedelta(hours=71), "Merci, je viens avec ma table.")

    def shop_talk(self, key, talk, moment, delivered):
        """A message of the conversation of an order, on the WhatsApp screen of the team."""
        account = self.whatsapp_account()
        order = self.shop_order_of(key)
        if not account or not order:
            return
        _when, who, kind, text = talk
        index = int(key.rsplit(":", 1)[1])
        parcel = self.shop_parcel(order, self.shop_stories(index)[0][0])
        partner = order.partner_id if who == "customer" else parcel.ocd_vendor_id
        if not partner:
            return
        channel = self.wa_channel(account, partner)
        if kind == "template":
            self.wa_template(account, channel, moment, text, order if text.startswith("whatsapp_cloud_sale.") else parcel)
            return
        courier = parcel.ocd_courier_id
        body = text.format(
            first=(order.partner_id.name or "").split(" ")[0],
            courier=(courier.name or "").split(" ")[0] if courier and courier != parcel.ocd_vendor_id else "Le livreur",
            vendor=parcel.ocd_vendor_id.name or "",
            delivered=scenario.hour_text(delivered),
        )
        if kind in ("in", "wait"):
            self.wa_in(account, channel, partner, moment, body, waiting=kind == "wait")
        elif kind == "out":
            self.wa_out(account, channel, moment, body)
        else:
            self.wa_note(channel, moment, body)

    def wa_channel(self, account, partner):
        number = partner._whatsapp_number()
        return self.env["discuss.channel"].sudo()._whatsapp_get_or_create(account, number, None, partner)

    def wa_dated(self, channel, message, date):
        message.sudo().write({"date": date})
        channel.sudo().write({"last_interest_dt": max(channel.last_interest_dt or date, date)})
        return date

    def wa_in(self, account, channel, partner, date, text, waiting=False):
        message = channel.with_context(whatsapp_skip_send=True).message_post(
            author_id=partner.id, body=text, message_type="whatsapp_message", subtype_xmlid="mail.mt_comment",
        )
        self.wa_dated(channel, message, date)
        self.env["whatsapp.message"].sudo().create({
            "account_id": account.id, "direction": "incoming", "state": "received", "message_type": "text",
            "body": text, "channel_id": channel.id, "mail_message_id": message.id, "partner_id": partner.id,
            "phone": channel.whatsapp_number, "model": "discuss.channel", "res_id": channel.id,
        })
        values = {"whatsapp_last_inbound_date": date, "whatsapp_waiting_since": date if waiting else False}
        channel.sudo().write(values)

    def wa_out(self, account, channel, date, text):
        team = self.env.ref("base.user_admin")
        message = channel.with_user(team).with_context(whatsapp_skip_send=True).message_post(
            body=text, message_type="whatsapp_message", subtype_xmlid="mail.mt_comment",
        )
        self.wa_dated(channel, message, date)
        self.env["whatsapp.message"].sudo().create({
            "account_id": account.id, "direction": "outgoing", "state": "read", "message_type": "text",
            "body": text, "channel_id": channel.id, "mail_message_id": message.id,
            "partner_id": channel.whatsapp_partner_id.id, "phone": channel.whatsapp_number,
            "model": "discuss.channel", "res_id": channel.id,
        })
        channel.sudo().write({"whatsapp_waiting_since": False, "whatsapp_state": "open"})

    def wa_note(self, channel, date, text):
        team = self.env.ref("base.user_admin")
        channel.with_user(team).execute_command_note(body=text)
        self.wa_dated(channel, channel.message_ids[:1], date)

    def wa_template(self, account, channel, date, xmlid, record):
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
            "account_id": account.id, "template_id": template.id, "direction": "outgoing", "state": "read",
            "message_type": "template", "body": template._fill_body(values), "partner_id": partner.id,
            "phone": channel.whatsapp_number, "model": record._name, "res_id": record.id,
        })
        message = channel._whatsapp_post_outgoing(wa_message)
        self.wa_dated(channel, message, date)


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
        if "ocd.cash.remittance" in env:
            # The cash handed over each evening by the couriers of the demo
            env["ocd.cash.remittance"].sudo().search([("courier_id", "in", partner_ids)]).unlink()
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
