"""The stores, the team and the life of the shop in the demo (chantiers 1, 2, 3, 10, 15 to 22): the
places of the vendors and the pieces of each store, the person of the team of Brenda, the orders
picked up at the store and at the relay point, a piece held to try, the reviews after the
deliveries, the followers, a report, the figures day by day, the promo of the week, the products
prepared for the next live. Mixed into hooks.OcdLiveDemo: each part only adds what is missing, and
a setup done once is never done again (what the team changes during a presentation stays)."""
import json
import logging
from datetime import datetime, time, timedelta

import pytz

from odoo import fields
from odoo.tools import SQL

from odoo.addons.ocd_live.models.ocd_vendor_count import _add_counts

from . import scenario

_logger = logging.getLogger(__name__)

MODULE = "ocd_live_demo"
# The settings of the shop the demo turned on, put back as they were when it is removed
PARAM_SHOP = "ocd_live_demo.shop_settings"
SHOP_SETTINGS = {"ocd_store_pickup": True, "ocd_hold_enabled": True, "ocd_relay_enabled": True}
# The steps done once (the setup of the demo): never forgotten by the pruning of the old steps
SETUP = "setup:"
# The days of visits of the stores kept (« itineraries this week »)
TAPS_DAYS = 14


class DemoShopLife:
    """The stores, the team and the life of the shop (mixed into hooks.OcdLiveDemo)."""

    def once(self, key, function, *args):
        """A setup of the demo, done once when it succeeds (retried at the next run else)."""
        Event = self.env["ocd.live.demo.event"].sudo()
        key = SETUP + key
        if Event.search_count([("key", "=", key)], limit=1):
            return None
        try:
            with self.env.cr.savepoint():
                result = function(*args)
                record = result if hasattr(result, "_name") and len(result) == 1 else None
                Event.create({"key": key, "res_model": record._name if record else False,
                              "res_id": record.id if record else False})
                return result
        except Exception:  # noqa: BLE001
            _logger.warning("OCD Live demo: %s could not be set up yet", key, exc_info=True)
            return None

    def done(self, key):
        """A step of the demo that takes place once (its key kept two weeks)."""
        Event = self.env["ocd.live.demo.event"].sudo()
        if Event.search_count([("key", "=", key)], limit=1):
            return True
        Event.create({"key": key})
        return False

    # === THE SETTINGS OF THE SHOP === #

    def shop_settings(self):
        """Pick up at the store, pieces held to try and relay points: on, as long as the demo is
        there (the settings the team had are kept and put back)."""
        params = self.env["ir.config_parameter"].sudo()
        if params.get_str(PARAM_SHOP):
            return
        company = self.company
        saved, values = {"company": company.id}, {}
        for name, value in SHOP_SETTINGS.items():
            if name in company._fields and company[name] != value:
                saved[name] = company[name]
                values[name] = value
        company.write(values)
        params.set_str(PARAM_SHOP, json.dumps(saved))

    # === THE PLACES OF THE VENDORS === #

    def demo_place(self, key):
        """The place `key` of the scenario (PLACES, or the relay point), else an empty recordset."""
        Place = self.env["ocd.vendor.place"].sudo().with_context(active_test=False)
        if key == scenario.RELAY_PLACE[0]:
            holder = self.ref(scenario.RELAY_PLACE[0])
            return Place.search([("vendor_id", "=", holder.id), ("relay", "=", True)], limit=1)
        row = next((row for row in scenario.PLACES if row[0] == key), None)
        if not row:
            return Place
        return Place.search([("vendor_id", "=", self.ref(row[1]).id), ("name", "=", row[3])], limit=1)

    def place_city(self, key, district):
        """The city of a place: of its district, else of the scenario (Lomé, when its module is there)."""
        if district:
            return district.city_id
        xmlid = scenario.PLACE_CITIES.get(key)
        city = self.env.ref(xmlid, raise_if_not_found=False) if xmlid else None
        if city:
            return city
        return self.env["res.city"].sudo().search([("country_id.code", "=", "TG"), ("name", "ilike", "Lom")], limit=1)

    def keep_places(self):
        for row in scenario.PLACES:
            self.once(f"place:{row[0]}", self.make_place, row)
        self.once("place:relay", self.make_relay_place)
        self.once("place:relay request", self.make_relay_request)
        brenda = self.ref("vendor_brenda")
        akwa = self.demo_place("akwa")
        if akwa and akwa.active and not brenda.ocd_departure_place_id:
            brenda.ocd_departure_place_id = akwa

    def make_place(self, row):
        """A place of a vendor, as the team accepted it. The first place of a vendor whose pieces
        are counted receives them: moved on the quants, without a stock move (the demo can be
        removed)."""
        key, vendor_xmlid, kind, name, district_xmlid, landmark, (latitude, longitude), state = row
        if self.demo_place(key):
            return self.demo_place(key)  # made by the team or a former demo: kept as it is
        vendor = self.ref(vendor_xmlid)
        district = self.env.ref(district_xmlid, raise_if_not_found=False) if district_xmlid else None
        values = {
            "name": name, "vendor_id": vendor.id, "kind": kind, "company_id": self.company.id,
            "city_id": self.place_city(key, district).id or False, "district_id": district.id if district else False,
            "landmark": landmark, "latitude": latitude, "longitude": longitude, "position_accuracy": 12,
            "state": state, "review_date": fields.Datetime.now() if state == "approved" else False,
        }
        if vendor._ocd_stock_in_places() and not vendor._ocd_stock_places():
            values["location_id"] = self.first_place_stock(vendor, name).id
        place = self.env["ocd.vendor.place"].sudo().create(values)
        place._ocd_set_hours(self.company._ocd_place_default_intervals())
        return place

    def first_place_stock(self, vendor, name):
        """The location of stock of the first place of `vendor`, with the pieces the vendor had in
        the stock of the shop."""
        root = self.env["product.product"]._ocd_stock_root(self.company)
        location = self.env["stock.location"].sudo().create({
            "name": f"{vendor.name} · {name}", "location_id": root.id, "usage": "internal",
            "company_id": root.company_id.id,
        })
        Quant = self.env["stock.quant"].sudo()
        for product, pieces in vendor._ocd_free_pieces(root, exact=True).items():
            Quant._update_available_quantity(product, root, -pieces)
            Quant._update_available_quantity(product, location, pieces)
        return location

    def make_relay_place(self):
        """The relay point of the demo: the shop of Rose in Bonamoussadi."""
        xmlid, name, district_xmlid, landmark, (latitude, longitude), capacity = scenario.RELAY_PLACE
        if self.demo_place(xmlid):
            return self.demo_place(xmlid)
        district = self.env.ref(district_xmlid)
        place = self.env["ocd.vendor.place"].sudo().create({
            "name": name, "vendor_id": self.ref(xmlid).id, "kind": "store", "company_id": self.company.id,
            "city_id": district.city_id.id, "district_id": district.id, "landmark": landmark,
            "latitude": latitude, "longitude": longitude, "position_accuracy": 10, "relay": True,
            "relay_capacity": capacity, "state": "approved", "review_date": fields.Datetime.now(),
        })
        place._ocd_set_hours(self.company._ocd_place_default_intervals())
        return place

    def make_relay_request(self):
        """A shop of Logpom asks to become a relay point (/points-relais): the team visits it."""
        xmlid, shop, district_xmlid, landmark, business = scenario.RELAY_REQUEST
        holder = self.ref(xmlid)
        district = self.env.ref(district_xmlid)
        return self.env["ocd.vendor.place"].sudo()._ocd_relay_request(
            shop, holder.name, holder.phone, holder.country_id, district, landmark, business,
        )

    def relay_point(self):
        place = self.demo_place(scenario.RELAY_PLACE[0])
        return place if place and place.active and place._ocd_relay_available() else self.env["ocd.vendor.place"]

    def collect_store(self):
        store = self.demo_place(scenario.SHOP_COLLECT_STORE)
        return store if store and store.active and self.company.ocd_store_pickup else self.env["ocd.vendor.place"]

    def place_stock(self, xmlid):
        """{location: quantities} of the stores of the product `xmlid` (PLACE_STOCK), when they all
        exist; None else (the stock of the shop, as before)."""
        rows = scenario.PLACE_STOCK.get(xmlid)
        if not rows:
            return None
        found = {}
        for key, quantities in rows.items():
            place = self.demo_place(key)
            if not place or not place.active:
                return None
            found[place._ocd_location()] = quantities
        return found

    # === THE TEAM === #

    def keep_team(self):
        for row in scenario.TEAM:
            self.once(f"team:{row[1]}", self.make_member, row)
            self.member_visit(row)

    def demo_member(self, row):
        """The member of the row in the team of the vendor: the contact of the demo, or the one
        already added with the same number (a team made by hand before the demo)."""
        vendor_xmlid, member_xmlid, _name, _place_key = row
        partner = self.ref(member_xmlid)
        members = self.env["ocd.vendor.member"].sudo().with_context(active_test=False).search([
            ("vendor_id", "=", self.ref(vendor_xmlid).id),
        ])
        digits = "".join(filter(str.isdigit, partner.phone or ""))
        return (members.filtered(lambda member: member.partner_id == partner)
                or members.filtered(lambda member: digits and "".join(filter(str.isdigit, member.phone or "")) == digits))[:1]

    def member_visit(self, row):
        """She opens her store space every morning when she opens the store (« Active »)."""
        member = self.demo_member(row)
        now = fields.Datetime.now()
        hours, minutes = (int(part) for part in scenario.TEAM_VISIT.split(":"))
        visit = self.shop_utc(datetime.combine(self.shop_today(now), time(hours, minutes)))
        if visit > now:
            visit -= timedelta(days=1)
        if member and (not member.last_visit or member.last_visit < visit):
            member.last_visit = visit

    def make_member(self, row):
        vendor_xmlid, member_xmlid, name, place_key = row
        vendor, partner, place = self.ref(vendor_xmlid), self.ref(member_xmlid), self.demo_place(place_key)
        if not place:
            raise ValueError(f"No place {place_key} yet")
        if not self.demo_member(row):
            self.env["ocd.vendor.member"].sudo()._ocd_add(vendor, name, partner.phone, place)

    # === THE PARCELS PICKED UP AT THE STORE AND AT THE RELAY POINT === #

    def parcel_done(self, parcel, moment):
        """A parcel handed over, without validating its stock transfer (the demo moves no stock),
        with the bill of its vendor when the accounting is there."""
        parcel.write({"ocd_stage": "delivered", "ocd_delivered_at": moment})
        if self.env["account.journal"].sudo().search_count(
            [("type", "=", "purchase"), ("company_id", "=", parcel.company_id.id)], limit=1
        ):
            self.step("the bill of the vendor", parcel._ocd_create_vendor_bills)

    def parcel_collect_ready(self, parcel, moment):
        if parcel.ocd_collect and parcel.ocd_stage == "to_prepare":
            parcel.action_ocd_collect_ready()
            parcel.write({"ocd_ready_at": moment, "ocd_code_sent_at": moment})

    def parcel_counter(self, parcel, moment):
        """Picked up at the counter of the store with the code, paid on the phone of the customer."""
        if not parcel.ocd_collect or parcel.ocd_stage != "ready":
            return
        if parcel.ocd_cod_state == "to_collect":
            parcel._ocd_collect("online", parcel.ocd_vendor_id)
            parcel.ocd_cod_collected_at = moment
        self.parcel_done(parcel, moment)

    def parcel_relay_receive(self, parcel, moment):
        if parcel.ocd_relay_id and parcel.ocd_stage == "on_the_way":
            parcel.ocd_relay_id._ocd_relay_receive(parcel)
            parcel.write({
                "ocd_relay_received_at": moment, "ocd_code_sent_at": moment,
                "ocd_relay_deadline": parcel._ocd_relay_deadline_from(moment),
            })

    def parcel_relay_hand_over(self, parcel, moment):
        """Picked up at the relay point with the code, paid on the phone (no cash at a relay point)."""
        if not parcel.ocd_relay_id or parcel.ocd_stage != "at_relay":
            return
        if parcel.ocd_cod_state == "to_collect":
            parcel._ocd_collect("online", parcel.ocd_relay_id.vendor_id)
            parcel.ocd_cod_collected_at = moment
        self.parcel_done(parcel, moment)
        if self.env["account.journal"].sudo().search_count(
            [("type", "=", "purchase"), ("company_id", "=", parcel.company_id.id)], limit=1
        ):
            self.step("the earning of the relay point", parcel._ocd_relay_earn)

    def review_step(self, key, vendor, story, moment):
        parcel = self.shop_parcel(self.shop_order_of(key), vendor)
        if parcel:
            self.parcel_review(parcel, moment, story)

    def review_of(self, parcel, story):
        """The stars and the word of the buyer: on the way the parcel came (late, at the store,
        at the relay point...), else on the product or the delivery."""
        choices = scenario.REVIEWS_BY_STORY.get(story)
        if not choices:
            products = parcel.move_ids.product_id.product_tmpl_id
            choices = [row for xmlid, rows in scenario.REVIEWS_BY_PRODUCT.items() if self.ref(xmlid) in products
                       for row in rows] + list(scenario.REVIEWS)
        return choices[scenario.number(parcel.name) % len(choices)]

    def parcel_review(self, parcel, moment, story=None):
        """The buyer gives a review of the vendor half an hour after the delivery."""
        if parcel.ocd_stage != "delivered":
            return
        Review = self.env["ocd.vendor.review"].sudo()
        if Review.search_count([("picking_id", "=", parcel.id)]):
            return
        stars, comment = self.review_of(parcel, story)
        review = Review._ocd_give(parcel, stars, comment or None)
        self.env.cr.execute(SQL("UPDATE ocd_vendor_review SET create_date = %s WHERE id = %s", moment, review.id))
        review.invalidate_recordset(["create_date"])

    def shop_hold(self, day, moment):
        """A piece held to try at the store of Bonapriso, asked in the morning."""
        customer, xmlid, variant_values, place_key, _asked, _accepted = scenario.HOLD
        place, partner = self.demo_place(place_key), self.ref(customer)
        if not place or not place.active:
            return None
        Hold = self.env["ocd.product.hold"].sudo()
        product = self.variant(xmlid, *variant_values)
        # One piece held at a time with a vendor
        if Hold.search_count([("partner_id", "=", partner.id), ("vendor_id", "=", place.vendor_id.id),
                              ("state", "in", ("requested", "accepted"))]):
            return None
        hold = Hold._ocd_request(place, product, partner)
        self.env.cr.execute(SQL("UPDATE ocd_product_hold SET create_date = %s WHERE id = %s", moment, hold.id))
        return hold

    def shop_hold_accept(self, day, moment):
        Hold = self.env["ocd.product.hold"].sudo()
        partner = self.ref(scenario.HOLD[0])
        hold = Hold.search([("partner_id", "=", partner.id), ("state", "=", "requested")], order="id desc", limit=1)
        if hold:
            hold.action_ocd_accept()

    def life_steps(self, day, at):
        """The steps of the life of the shop of a day: the piece held to try and its answer."""
        _customer, _xmlid, _values, _place, asked, accepted = scenario.HOLD
        return [
            (at(asked), f"hold:{day}", self.shop_hold, (day, self.shop_utc(at(asked)))),
            (at(accepted), f"hold:{day}:accepted", self.shop_hold_accept, (day, self.shop_utc(at(accepted)))),
        ]

    def review_steps(self, key, index, day, vendor, story, ordered):
        """The review of a parcel, after its delivery (most buyers give one)."""
        if scenario.number(day, index, vendor.id) % scenario.REVIEW_SKIP == 0:
            return []
        delivered = next(
            (scenario.when(ordered, step_time) for name, step_time in scenario.STORIES[story]
             if name.startswith("deliver") or name in ("counter", "relay_hand_over")),
            None,
        )
        if not delivered:
            return []
        moment = delivered + timedelta(minutes=scenario.REVIEW_AFTER_MINUTES)
        return [(moment, f"{key}:{vendor.id}:review", self.review_step, (key, vendor, story, self.shop_utc(moment)))]

    # === THE LIFE OF THE SHOP === #

    def keep_life(self, now):
        self.once("followers", self.make_followers)
        self.once("stock alerts", self.make_stock_alerts)
        self.once("verified vendors", self.make_verified)
        self.once("change to check", self.make_change)
        self.step("the report of the week", self.keep_report, now)
        self.step("the promo of the week", self.keep_promo, now)
        self.step("the prepared lives", self.keep_prepared, now)
        self.step("the visits of the stores", self.keep_taps, now)
        self.step("the figures of the vendors", self.keep_figures, now)

    def make_followers(self):
        """The followers of the vendors, who followed over the last months."""
        Follower = self.env["ocd.vendor.follower"].sudo()
        now = fields.Datetime.now()
        for vendor_xmlid, customers in scenario.FOLLOWERS.items():
            vendor = self.ref(vendor_xmlid)
            for index, customer in enumerate(customers):
                follower = Follower._ocd_follow(vendor, self.ref(customer), lives=True, news=index % 3 != 2,
                                                source=("boutique", "feed", "product")[index % 3])
                days = scenario.FOLLOWED_DAYS_AGO[index % len(scenario.FOLLOWED_DAYS_AGO)]
                follower.followed_at = now - timedelta(days=days)

    # === THE SALES OF THE LIVES === #

    def live_bookings(self, day):
        """The lives of the vendors of the shop on `day` (Douala): (xmlid, vendor, booking)."""
        start = self.shop_utc(datetime.combine(day, time()))
        end = self.shop_utc(datetime.combine(day + timedelta(days=1), time()))
        rows = []
        for xmlid in scenario.LIVE_SALES:
            vendor = self.ref(xmlid)
            for booking in self.Booking.search([
                ("partner_id", "=", vendor.id), ("state", "in", ("confirmed", "done")),
                ("start_datetime", ">=", start), ("start_datetime", "<", end),
            ]):
                rows.append((xmlid, vendor, booking))
        return rows

    def live_steps(self, day):
        """The steps of the lives of the day of the vendors of the shop: a viewer follows, the
        visits of the boutique, the orders of the customers who came from the live and their
        parcels (the next morning)."""
        steps = []
        tz = pytz.timezone(scenario.SHOP_TZ)
        for xmlid, vendor, booking in self.live_bookings(day):
            started = pytz.utc.localize(booking.start_datetime).astimezone(tz).replace(tzinfo=None)
            key = f"live:{booking.id}"
            for minutes, name, function in ((scenario.LIVE_FOLLOW_AFTER, "follow", self.live_follow),
                                            (scenario.LIVE_VISITS_AFTER, "visits", self.live_visits)):
                moment = started + timedelta(minutes=minutes)
                steps.append((moment, f"{key}:{name}", function, (booking, self.shop_utc(moment))))
            story = "vendor_evening" if vendor.ocd_delivery_mode == "vendor" else "live"
            for index, (minutes, _lines) in enumerate(scenario.LIVE_SALES[xmlid]):
                ordered = started + timedelta(minutes=minutes)
                order_key = f"{key}:{index}"
                steps.append((ordered, f"{order_key}:order", self.live_order, (order_key, booking, xmlid, index, ordered)))
                for number, (name, step_time) in enumerate(scenario.STORIES[story]):
                    moment = scenario.when(ordered, step_time)
                    steps.append((moment, f"{order_key}:{vendor.id}:{number}:{name}", self.shop_parcel_step,
                                  (order_key, vendor, name, self.shop_utc(moment))))
                steps.extend(self.review_steps(order_key, index, day, vendor, story, ordered))
        return steps

    def live_running(self, booking):
        return booking.exists() and booking.state in ("confirmed", "done")

    def live_order(self, key, booking, xmlid, index, ordered):
        """An order placed during the live by a customer who came to the boutique from it: it
        counts for the live (« My lives » of the vendor)."""
        if not self.live_running(booking):
            return None
        _minutes, lines = scenario.LIVE_SALES[xmlid][index]
        customers = scenario.LIVE_CUSTOMERS
        customer = customers[(scenario.number(booking.id) + index) % len(customers)]
        self.keep_stock()
        order = self.order(self.ref(customer), self.order_lines(lines, booking.id, index), live=booking)
        return self.dated_order(order, ordered)

    def live_visits(self, booking, moment):
        """The visits of the boutique during the live (the control room counts them live)."""
        if not self.live_running(booking):
            return
        low, more = scenario.LIVE_VISITS
        visits = low + scenario.number(booking.id, "visits") % more
        self.env.cr.execute(SQL(
            "UPDATE ocd_live_booking SET ocd_visit_count = GREATEST(COALESCE(ocd_visit_count, 0), %s) WHERE id = %s",
            visits, booking.id,
        ))
        booking.invalidate_recordset(["ocd_visit_count"])

    def live_follow(self, booking, moment):
        """A viewer follows the vendor during the live. The demo has a few customers: the one who
        followed the longest ago follows again from this live (the lives before keep theirs
        until the vendor has done as many lives as followers)."""
        if not self.live_running(booking):
            return
        self.once("followers", self.make_followers)
        follower = self.env["ocd.vendor.follower"].sudo().search([
            ("vendor_id", "=", booking.partner_id.id), ("followed_at", "<", booking.start_datetime),
        ], order="followed_at, id", limit=1)
        if follower:
            follower.followed_at = moment

    def make_stock_alerts(self):
        Alert = self.env["ocd.stock.alert"].sudo()
        for xmlid, values, customers in scenario.STOCK_ALERTS:
            product = self.variant(xmlid, *values)
            for customer in customers:
                partner = self.ref(customer)
                Alert._ocd_register(product, phone=partner.phone, partner=partner)

    def make_verified(self):
        for xmlid in scenario.VERIFIED:
            self.ref(xmlid).ocd_verified = True

    def make_change(self):
        xmlid, new_name = scenario.CHANGE
        self.ref(xmlid).write({
            "ocd_change_name": new_name, "ocd_change_state": "to_check", "ocd_change_date": fields.Datetime.now(),
        })

    def week_start(self, now):
        local = pytz.utc.localize(now).astimezone(pytz.timezone(scenario.SHOP_TZ)).date()
        return local - timedelta(days=local.weekday())

    def keep_report(self, now):
        """A report of a customer waits for the team each week (« To check »)."""
        monday = self.week_start(now)
        Report = self.env["ocd.report"].sudo()
        xmlid, customer, reason, note = scenario.REPORT
        product = self.ref(xmlid)
        if self.done(f"report:{monday}") or not product.is_published:
            return
        if not Report.search_count([("product_id", "=", product.id), ("state", "=", "new")]):
            Report._ocd_create(reason, note, product=product, partner=self.ref(customer))

    def keep_promo(self, now):
        """The promo of the week of Brenda, from Monday to Sunday evening."""
        monday = self.week_start(now)
        if self.done(f"promo:{monday}"):
            return
        xmlid, share = scenario.PROMO
        product = self.ref(xmlid)
        price = round(product.list_price * share / 100) * 100
        tz = pytz.timezone(scenario.SHOP_TZ)
        end = tz.localize(datetime.combine(monday + timedelta(days=6), time(23, 0))).astimezone(pytz.utc).replace(tzinfo=None)
        self.env["ocd.product.promo"].sudo()._ocd_put(product, price, end, source="vendor")

    def keep_prepared(self, now):
        """The next lives of Brenda are prepared: the products the host shows, in their order."""
        vendor_xmlid, xmlids, note = scenario.PREPARED
        vendor = self.ref(vendor_xmlid)
        products = self.env["product.template"].browse([self.ref(xmlid).id for xmlid in xmlids])
        for booking in self.Booking.search([
            ("partner_id", "=", vendor.id), ("state", "=", "confirmed"),
            ("start_datetime", ">", now), ("start_datetime", "<", now + timedelta(days=3)),
        ]):
            if not booking._ocd_prepared_products():
                self.step("a live prepared", booking._ocd_prepare, products, note)

    def keep_taps(self, now):
        """The visits of the stores thanks to OCD (itinerary, call, WhatsApp), day by day."""
        Tap = self.env["ocd.vendor.place.tap"].sudo()
        today = self.shop_today(now)
        for offset in range(TAPS_DAYS, 0, -1):
            day = today - timedelta(days=offset)
            if self.done(f"taps:{day}"):
                continue
            for key, kinds in scenario.PLACE_TAPS.items():
                place = self.demo_place(key)
                if not place or place.state != "approved":
                    continue
                for kind, count in kinds:
                    for number in range(count + scenario.number(key, day, kind) % 2):
                        tap = Tap.create({"place_id": place.id, "kind": kind})
                        moment = self.shop_utc(datetime.combine(day, time(9 + (number * 3) % 10, 15)))
                        self.env.cr.execute(SQL("UPDATE ocd_vendor_place_tap SET create_date = %s WHERE id = %s",
                                                moment, tap.id))

    def keep_figures(self, now):
        """The visits of the boutiques, the WhatsApp contacts and the lives opened from OCD, day by
        day (the figures of the vendors): busier on Friday and Saturday, growing over the months."""
        today = self.today()
        vendors = self.partners().filtered(lambda partner: partner.ocd_is_vendor and partner.ocd_vendor_state == "approved")
        names = {data.res_id: data.name for data in self.env["ir.model.data"].sudo().search([
            ("module", "=", MODULE), ("model", "=", "res.partner"), ("res_id", "in", vendors.ids),
        ])}
        for offset in range(scenario.FIGURES_DAYS, 0, -1):
            day = today - timedelta(days=offset)
            if self.done(f"figures:{day}"):
                continue
            growth = 0.7 + 0.4 * (scenario.FIGURES_DAYS - offset) / scenario.FIGURES_DAYS
            weekday = (0.9, 0.85, 0.9, 1.0, 1.25, 1.4, 0.8)[day.weekday()]
            counts = {}
            for vendor in vendors:
                xmlid = names.get(vendor.id, "")
                base = scenario.FIGURES.get(xmlid, scenario.FIGURES_OTHERS)
                for kind, value in zip(("visit", "contact", "watch"), base):
                    noise = 0.8 + (scenario.number(xmlid, day, kind) % 41) / 100
                    count = int(round(value * growth * weekday * noise))
                    if count:
                        counts[(vendor.id, day, kind, 0)] = count
                # The lives of the day of the vendor: opened from OCD, live by live
                start = datetime.combine(day, time())
                for booking in self.Booking.search([
                    ("partner_id", "=", vendor.id), ("state", "in", ("confirmed", "done")),
                    ("start_datetime", ">=", start), ("start_datetime", "<", start + timedelta(days=1)),
                ]):
                    counts[(vendor.id, day, "watch", booking.id)] = 12 + scenario.number(booking.id) % 30
            if counts:
                _add_counts(self.env.cr, counts)
