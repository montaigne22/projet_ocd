"""The demo of the modules around the shop, when they are installed (before or after the demo):
OCD Business, the ambassadors, the big events, the clips, OCD Vote and OCD Tickets. Each one is set up once (ocd.live.demo.event
`setup:...`, with the record it made), kept on the days around today by the scheduled action,
and removed at the uninstallation (hooks.py)."""
from datetime import datetime, time, timedelta

import pytz

from odoo import Command, fields
from odoo.tools import BinaryBytes
from odoo.tools.misc import file_open

from odoo.addons.ocd_live.models.ocd_vendor_count import _add_counts

from . import scenario

MODULE = "ocd_live_demo"


class DemoModules:
    """The part of OcdLiveDemo (hooks.py) for the modules around the shop."""

    def has(self, model):
        return model in self.env

    def setup_record(self, key):
        """The record made by the setup `key` (once), else None."""
        event = self.env["ocd.live.demo.event"].sudo().search([("key", "=", "setup:" + key)], limit=1)
        if event.res_model and event.res_model in self.env and event.res_id:
            return self.env[event.res_model].sudo().browse(event.res_id).exists() or None
        return None

    def local_now(self, now):
        return pytz.utc.localize(now).astimezone(pytz.timezone(scenario.SHOP_TZ)).replace(tzinfo=None)

    def keep_modules(self, now):
        self.step("OCD Business", self.keep_business, now)
        self.step("the ambassadors", self.keep_ambassadors, now)
        self.step("the big events", self.keep_evenings, now)
        self.step("the clips", self.keep_clips, now)
        self.step("OCD Vote", self.keep_vote, now)
        self.step("OCD Tickets", self.keep_tickets, now)

    # === OCD BUSINESS === #

    def keep_business(self, now):
        """The formulas of the vendors, their dates kept from today: Brenda in the middle of her
        three months, Kossi offered a month, Junior at the end of his month, Fatou ended."""
        if not self.has("ocd.business.period"):
            return
        for row in scenario.BUSINESS:
            self.once(f"business:{row[0]}", self.make_business, row)
            period = self.setup_record(f"business:{row[0]}")
            if period:
                self.step(f"the formula of {row[0]}", self.business_dates, period, row)

    def make_business(self, row):
        """The formula of the vendor: paid with its order (and its invoice), or offered by the team."""
        xmlid, kind, product_xmlid, _started, days, why = row
        vendor = self.ref(xmlid)
        Period = self.env["ocd.business.period"].sudo()
        if kind != "paid":
            return Period._ocd_add(vendor, days, kind, note=why or None)
        product = self.env.ref(product_xmlid).product_variant_id
        order = self.SaleOrder.create({
            "partner_id": vendor.id,
            "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 1, "tax_ids": [Command.clear()]})],
        })
        order.action_confirm()
        return Period.search([("sale_order_id", "=", order.id)], limit=1)

    def business_dates(self, period, row):
        """The dates of the formula from the day of the vendor (the period chain of a vendor is
        never touched when the team added one after it)."""
        _xmlid, _kind, _product, started, _days, _why = row
        vendor = period.vendor_id
        Period = self.env["ocd.business.period"].sudo()
        if period.state == "cancelled" or Period.search_count([("vendor_id", "=", vendor.id), ("id", ">", period.id)]):
            return
        today = vendor._ocd_business_today()
        start = today - timedelta(days=started)
        end = start + timedelta(days=period.days - 1)
        if (period.date_start, period.date_end) == (start, end):
            return
        period.write({"date_start": start, "date_end": end, "state": Period._ocd_state_for(start, end, today)})
        moment = self.shop_utc(datetime.combine(start, time(10, 15)))
        self.env.cr.execute("UPDATE ocd_business_period SET create_date = %s WHERE id = %s", [moment, period.id])
        if period.sale_order_id:
            period.sale_order_id.date_order = moment
        period.invalidate_recordset(["create_date"])
        vendor._ocd_business_refresh()

    # === THE AMBASSADORS === #

    def ambassador(self):
        """Grâce, the ambassador of the demo, once she is set up (else None)."""
        if not self.has("ocd.ambassador.gain"):
            return None
        grace = self.ref(scenario.AMBASSADOR[0])
        return grace if grace.ocd_ambassador_state == "active" else None

    def ambassador_of(self, day, index):
        """The ambassador whose link brought the order `index` of `day`: one order in turn every
        AMBASSADOR_EVERY days (never the same customer too often in a month)."""
        grace = self.ambassador()
        if not grace or day.toordinal() % scenario.AMBASSADOR_EVERY:
            return None
        orders = scenario.AMBASSADOR_ORDERS
        return grace if orders[(day.toordinal() // scenario.AMBASSADOR_EVERY) % len(orders)] == index else None

    def setup_ambassadors(self):
        if self.has("ocd.ambassador.gain"):
            self.once("ambassador", self.make_ambassador)
            self.once("ambassador asking", self.make_ambassador_asking)

    def keep_ambassadors(self, now):
        grace = self.ambassador()
        if not grace:
            return
        self.once("ambassador history", self.make_ambassador_history, grace, now)
        self.step("the gains of the ambassador", self.ambassador_gains, grace)
        self.step("the dates of the ambassador", self.ambassador_dates, grace)
        self.step("the visits of the ambassador", self.ambassador_visits, grace, now)
        self.step("the payout of the ambassador", self.ambassador_payout, grace, now)

    def make_ambassador(self):
        """Grâce shares the products of the shop with her link, paid every Monday by Mobile Money."""
        xmlid, code, days = scenario.AMBASSADOR
        grace = self.ref(xmlid)
        Partner = self.env["res.partner"].sudo()
        if Partner.search_count([("ocd_ambassador_code", "=", code), ("id", "!=", grace.id)]):
            code = Partner._ocd_new_ambassador_code(grace.name)
        since = fields.Datetime.now() - timedelta(days=days)
        grace.write({
            "ocd_ambassador_state": "active", "ocd_ambassador_code": code, "ocd_ambassador_since": since.date(),
            "ocd_ambassador_charter_at": since, "ocd_ambassador_momo_since": since, "ocd_ambassador_id_checked": True,
        })
        return grace

    def make_ambassador_asking(self):
        """Kevin asked to become an ambassador: the team checks him (« To check »)."""
        kevin = self.ref(scenario.AMBASSADOR_ASKING)
        kevin.write({"ocd_ambassador_state": "requested", "ocd_ambassador_charter_at": fields.Datetime.now()})
        return kevin

    def make_ambassador_history(self, grace, now):
        """Her orders before the days of the shop: delivered, their gains confirmed and paid with
        her payout of last Monday."""
        today = self.shop_today(now)
        self.keep_stock()
        for days, customer, xmlid, quantity in scenario.AMBASSADOR_PAST:
            ordered = datetime.combine(today - timedelta(days=days), time(11, 40))
            order = self.order(self.ref(customer), [(self.variant(xmlid), quantity)],
                               ambassador=grace, linked=now - timedelta(hours=1))
            self.dated_order(order, ordered)
            order.ocd_ambassador_at = self.shop_utc(ordered - timedelta(minutes=scenario.AMBASSADOR_LINK_MINUTES))
            delivered = self.shop_utc(ordered + timedelta(hours=4))
            for parcel in order.picking_ids.filtered("ocd_is_parcel"):
                if parcel.ocd_cod_state == "to_collect":
                    parcel._ocd_collect("online", parcel.ocd_vendor_id)
                    parcel.ocd_cod_collected_at = delivered
                self.parcel_done(parcel, delivered)
        self.ambassador_gains(grace)
        monday = today - timedelta(days=today.weekday())
        self.ambassador_pay(grace, monday)

    def ambassador_gains(self, grace):
        """Her parcels delivered (at the door, at the store, at the relay point): their gains
        delivered; those whose day came, confirmed (a bill each, with the accounting)."""
        Gain = self.env["ocd.ambassador.gain"].sudo()
        waiting = Gain.search([("ambassador_id", "=", grace.id), ("state", "=", "ordered")])
        delivered = waiting.picking_id.filtered(lambda parcel: parcel.ocd_stage == "delivered")
        if delivered:
            Gain._ocd_parcels_delivered(delivered)
        if not self.env["account.journal"].sudo().search_count([("type", "=", "purchase")], limit=1):
            return
        today = self.company._ocd_local_today()
        due = Gain.search([("ambassador_id", "=", grace.id), ("state", "=", "delivered"),
                           ("confirm_on", "<=", today), ("bill_id", "=", False)])
        for gain in due:
            self.step("a gain confirmed", gain._ocd_confirm)

    def ambassador_payout(self, grace, now):
        """Every Monday: her payout prepared at 7:00 and paid by the team at 10:00."""
        local = self.local_now(now)
        monday = local.date() - timedelta(days=local.weekday())
        hours, minutes = (int(part) for part in scenario.AMBASSADOR_PAYOUT.split(":"))
        paid_at = datetime.combine(monday, time(hours, minutes))
        if local >= paid_at and not self.done(f"ambassador payout:{monday}"):
            self.ambassador_pay(grace, monday)

    def ambassador_pay(self, grace, monday):
        """Her payout of Monday, paid by Mobile Money and recorded in the accounting (« My money »
        shows it paid, the next one to come)."""
        for payout in self.env["ocd.payout"].sudo()._ocd_prepare(vendors=grace, day=monday):
            payout.payment_reference = scenario.PAYOUT_REFERENCE % f"{monday:%d%m}-{payout.id}"
            self.step("the payout of the ambassador paid", self.pay_payout, payout)

    def pay_payout(self, payout):
        payout.action_validate()
        payout.action_register_payment()

    def ambassador_visits(self, grace, now):
        """The visits by her links, day by day over the last month (her figures)."""
        today = self.today()
        products = [self.ref(xmlid) for xmlid in scenario.AMBASSADOR_SHARED]
        for offset in range(scenario.AMBASSADOR_VISIT_DAYS, 0, -1):
            day = today - timedelta(days=offset)
            if self.done(f"ambassador visits:{day}"):
                continue
            counts = {}
            for product in products:
                count = scenario.AMBASSADOR_VISITS[0] + scenario.number(grace.id, day, product.id) % scenario.AMBASSADOR_VISITS[1]
                counts[(grace.id, day, "ambassador_visit", product.id)] = count
            _add_counts(self.env.cr, counts)

    def ambassador_dates(self, grace):
        """Her orders and gains dated from the order (made later by the demo)."""
        self.env.cr.execute("""
            UPDATE ocd_ambassador_gain g SET create_date = o.date_order FROM sale_order o
             WHERE g.order_id = o.id AND g.ambassador_id = %s AND g.create_date > o.date_order + interval '1 hour'
        """, [grace.id])
        self.env.cr.execute("""
            UPDATE sale_order SET create_date = date_order
             WHERE ocd_ambassador_id = %s AND create_date > date_order + interval '1 hour'
        """, [grace.id])
        self.env["ocd.ambassador.gain"].invalidate_model(["create_date"])
        self.env["sale.order"].invalidate_model(["create_date"])

    # === THE BIG EVENTS === #

    def keep_evenings(self, now):
        """« Vendredi wax » every Friday evening in Cameroon: the next two, made when their week
        comes; Brenda joins with her promos (accepted), Fatou sent hers (to check), customers
        asked to be told."""
        if not self.has("ocd.evening"):
            return
        local = self.local_now(now)
        _name, weekday, start_hour, end_hour, _countries = scenario.EVENING
        days = (weekday - local.weekday()) % 7
        first = local.date() + timedelta(days=days)
        if datetime.combine(first, time(end_hour)) <= local:
            first += timedelta(days=7)
        for friday in (first, first + timedelta(days=7)):
            self.once(f"evening:{friday}", self.make_evening, friday)

    def make_evening(self, day):
        name, _weekday, start_hour, end_hour, countries = scenario.EVENING
        start = self.shop_utc(datetime.combine(day, time(start_hour)))
        # Made late (the demo installed on the day): the vendors still join, until the start
        registration_end = max(self.shop_utc(datetime.combine(day, time(scenario.EVENING_REGISTRATION_UNTIL))),
                               fields.Datetime.now() + timedelta(minutes=5))
        evening = self.env["ocd.evening"].sudo().create({
            "name": f"{name} du {day.day} {scenario.MONTHS[day.month - 1]}",
            "description": scenario.EVENING_DESCRIPTION,
            "date_start": start,
            "date_end": start + timedelta(hours=end_hour - start_hour),
            "registration_end": min(registration_end, start + timedelta(hours=end_hour - start_hour)),
            "country_ids": [Command.set([self.env.ref(xmlid).id for xmlid in countries])],
            "max_discount": scenario.EVENING_MAX_DISCOUNT,
        })
        evening.action_ocd_open()
        Participation = self.env["ocd.evening.participation"].sudo()
        for vendor_xmlid, products, approved in scenario.EVENING_VENDORS:
            prices = {}
            for xmlid, discount in products:
                template = self.ref(xmlid)
                prices[template] = round(template.list_price * (100 - discount) / 100 / 100) * 100
            participation = Participation._ocd_submit(evening, self.ref(vendor_xmlid), prices)
            if approved:
                participation.action_ocd_approve()
        Alert = self.env["ocd.evening.alert"].sudo()
        for customer in scenario.EVENING_ALERTS:
            Alert.create({"evening_id": evening.id, "partner_id": self.ref(customer).id})
        return evening

    # === THE CLIPS === #

    def keep_clips(self, now):
        """The clips of the replays of Awa: one per product shown, made from her short video (the
        demo makes no video), played and visited day by day."""
        if not self.has("ocd.live.clip"):
            return
        awa = self.ref(scenario.CLIPS_VENDOR)
        Clip = self.env["ocd.live.clip"].sudo().with_context(active_test=False)
        bookings = self.Booking.search([
            ("partner_id", "=", awa.id), ("state", "in", ("confirmed", "done")), ("replay_published", "=", True),
            ("start_datetime", ">=", now - timedelta(days=scenario.PAST_DAYS)),
        ])
        for booking in bookings:
            for moment in booking.moment_ids:
                if moment.product_tmpl_id and not Clip.search_count([("booking_id", "=", booking.id),
                                                                     ("moment_id", "=", moment.id)]):
                    self.step("a clip of Awa", self.make_clip, booking, moment)
        self.step("the plays of the clips", self.clip_counts, awa)

    def make_clip(self, booking, moment):
        product = moment.product_tmpl_id
        Clip = self.env["ocd.live.clip"].sudo()
        raw = file_open(f"{MODULE}/static/video/{scenario.CLIPS_VIDEO}", "rb").read()
        video = BinaryBytes(raw, filename=scenario.CLIPS_VIDEO)
        made = booking.end_datetime + timedelta(minutes=scenario.CLIPS_MADE_AFTER)
        clip = Clip.create({
            "booking_id": booking.id,
            "moment_id": moment.id,
            "product_tmpl_id": product.id,
            "code": Clip._ocd_new_code(),
            "start": float(moment.offset_seconds),
            "duration": scenario.CLIPS_SECONDS,
        })
        clip.write({
            "state": "ready", "video": video, "video_size": len(raw), "poster": product.image_1024,
            "made_at": made, "version": 1,
        })
        return clip

    def clip_counts(self, awa):
        """Plays and visits of each clip, from the day it was made."""
        today = self.today()
        counts = {}
        for clip in self.env["ocd.live.clip"].sudo().search([("vendor_id", "=", awa.id), ("state", "=", "ready")]):
            first = (clip.made_at or clip.create_date).date()
            for offset in range((today - first).days):
                day = first + timedelta(days=offset)
                key = f"clip:{clip.id}:{day}"
                if self.done(key):
                    continue
                age = 1 + offset
                plays = scenario.CLIPS_PLAYS[0] + scenario.number(clip.id, day) % scenario.CLIPS_PLAYS[1]
                counts[(awa.id, day, "clip_play", clip.id)] = max(plays // age, 3)
                counts[(awa.id, day, "clip_visit", clip.id)] = max(plays // (age * 6), 1)
        if counts:
            _add_counts(self.env.cr, counts)

    # === OCD VOTE === #

    def keep_vote(self, now):
        """« Le meilleur plat de Douala »: the contest of a festival, its cooks and their dishes,
        the votes paid every day; the votes close in the days to come (the final on TikTok)."""
        if not self.has("ocd.vote.contest"):
            return
        self.once("vote organizer", self.make_organizer)
        self.once("vote contest", self.make_contest, now)
        contest = self.setup_record("vote contest")
        if not contest or contest.state != "approved":
            return
        self.step("the end of the contest", self.contest_dates, contest, now)
        local = self.local_now(now)
        for offset in range(-scenario.SHOP_PAST_DAYS, 1):
            day = local.date() + timedelta(days=offset)
            for index, (hour, candidate, votes, customer) in enumerate(scenario.VOTES):
                hours, minutes = (int(part) for part in hour.split(":"))
                moment = datetime.combine(day, time(hours, minutes))
                if moment > local or self.shop_utc(moment) < contest.date_open:
                    continue
                key = f"vote:{day}:{index}"
                if not self.done(key):
                    self.step("a vote paid", self.vote_paid, contest, candidate, votes, customer, self.shop_utc(moment))

    def make_organizer(self):
        """The organiser of the contest and of the concert: checked by the team."""
        organizer = self.ref(scenario.ORGANIZER)
        organizer.write({"ocd_vote_organizer": True, "ocd_vote_organizer_verified": True})
        return organizer

    def make_contest(self, now):
        name, description, prize, open_days, close_days = scenario.CONTEST
        Contest = self.env["ocd.vote.contest"].sudo()
        contest = Contest.create({
            "name": name, "description": description, "prize": prize,
            "organizer_id": self.ref(scenario.ORGANIZER).id, "country_id": self.env.ref("base.cm").id,
            "city": "Douala", "date_open": now - timedelta(days=open_days),
            "date_close": self.contest_close(now, close_days),
            "image": self.demo_image(scenario.CONTEST_IMAGE),
        })
        Candidate = self.env["ocd.vote.candidate"].sudo()
        for candidate_name, bio, district, image in scenario.CANDIDATES:
            Candidate.create({
                "contest_id": contest.id, "name": candidate_name, "bio": bio, "city": district,
                "photo": self.demo_image(image),
            })
        contest.action_ocd_send_to_check()
        contest.action_ocd_approve()
        return contest

    def demo_image(self, name):
        return BinaryBytes(file_open(f"{MODULE}/static/img/{name}", "rb").read(), filename=name)

    def contest_close(self, now, days):
        local = self.local_now(now).date() + timedelta(days=days)
        return self.shop_utc(datetime.combine(local, time(scenario.CONTEST_CLOSE_HOUR)))

    def contest_dates(self, contest, now):
        """The votes close in the days to come, whatever the day of the presentation (never
        earlier than set: the team may have moved it later)."""
        close = self.contest_close(now, scenario.CONTEST[4])
        if contest.date_close < close:
            contest.write({"date_close": close, "final_at": close + timedelta(hours=1)})

    def vote_paid(self, contest, candidate_index, votes, customer, moment):
        candidates = contest.candidate_ids.sorted("number")
        if candidate_index >= len(candidates) or not contest._ocd_is_open():
            return
        Vote = self.env["ocd.vote"].sudo()
        vote = Vote._ocd_create(candidates[candidate_index], votes, self.ref(customer), source="page")
        vote.order_id.action_confirm()
        vote.order_id.date_order = moment
        self.env.cr.execute("UPDATE ocd_vote SET create_date = %s, paid_at = %s WHERE id = %s", [moment, moment, vote.id])
        vote.invalidate_recordset(["create_date", "paid_at"])
        return vote

    # === OCD TICKETS === #

    def keep_tickets(self, now):
        """« Nuit de l'Afrobeat » every Saturday night in Douala: put on sale two weeks before,
        tickets sold every day, Junior at the gate."""
        if not self.has("ocd.ticket.controller"):
            return
        self.once("vote organizer", self.make_organizer)
        local = self.local_now(now)
        name, weekday, hour, hours = scenario.CONCERT[:4]
        days = (weekday - local.weekday()) % 7
        first = local.date() + timedelta(days=days)
        if datetime.combine(first, time(hour)) + timedelta(hours=hours) <= local:
            first += timedelta(days=7)
        for saturday in (first, first + timedelta(days=7)):
            self.once(f"concert:{saturday}", self.make_concert, saturday)
        for offset in range(-scenario.SHOP_PAST_DAYS, 1):
            day = local.date() + timedelta(days=offset)
            for index, (at, kinds, customer) in enumerate(scenario.TICKET_SALES):
                hours_at, minutes_at = (int(part) for part in at.split(":"))
                moment = datetime.combine(day, time(hours_at, minutes_at))
                if moment > local:
                    continue
                key = f"tickets:{day}:{index}"
                if not self.done(key):
                    self.step("tickets sold", self.tickets_sold, day, kinds, customer, self.shop_utc(moment))

    def make_concert(self, day):
        name, _weekday, hour, hours, kind, about, hall = scenario.CONCERT
        start = self.shop_utc(datetime.combine(day, time(hour)))
        event = self.env["event.event"].sudo().create({
            "name": name,
            "ocd_ticketing": True,
            "ocd_organizer_id": self.ref(scenario.ORGANIZER).id,
            "ocd_kind": kind,
            "date_begin": start,
            "date_end": start + timedelta(hours=hours),
            "ocd_doors_at": start - timedelta(minutes=scenario.CONCERT_DOORS_BEFORE),
            "date_tz": scenario.SHOP_TZ,
            "address_id": self.ref(hall).id,
            "ocd_about": about,
            "event_ticket_ids": [Command.create({"name": ticket, "price": price, "seats_max": seats, "description": text})
                                 for ticket, price, seats, text in scenario.TICKETS],
        })
        event.action_ocd_send_to_check()
        event.action_ocd_approve()
        gate_name, gate, controller = scenario.CONTROLLER
        self.env["ocd.ticket.controller"].sudo().create({
            "event_id": event.id, "partner_id": self.ref(controller).id, "name": gate_name, "gate": gate,
        })
        return event

    def tickets_sold(self, day, kinds, customer, moment):
        """Tickets of the next concert on sale, paid on the phone."""
        events = self.env["event.event"].sudo().search([
            ("ocd_organizer_id", "=", self.ref(scenario.ORGANIZER).id), ("ocd_state", "=", "approved"),
            ("date_begin", ">", moment), ("name", "=", scenario.CONCERT[0]),
        ], order="date_begin", limit=1)
        if not events or not events._ocd_on_sale():
            return
        tickets = {ticket.name: ticket for ticket in events.event_ticket_ids}
        # A kind sold out stays sold out (« Sold out » on the page)
        quantities = {tickets[name]: count for name, count in kinds if name in tickets
                      and (not tickets[name].seats_max or tickets[name].seats_available >= count)}
        if not quantities:
            return
        partner = self.ref(customer)
        order = self.SaleOrder._ocd_ticket_create(events, quantities, partner, partner.name)
        order.action_confirm()
        order.date_order = moment
        return order
