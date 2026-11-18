from datetime import datetime, time, timedelta

from odoo import fields, models

# The parts of a day of the couriers
PARTS = [("morning", "Morning"), ("afternoon", "Afternoon"), ("evening", "Evening")]


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_express_open_to = fields.Selection(
        selection=[("invited", "Invited senders"), ("all", "Everybody")],
        string="OCD Express Open To", default="invited", required=True,
        help="Invited: a request goes to the team, who opens the account. Everybody: the account opens "
        "with the number checked on WhatsApp.",
    )
    ocd_express_city_ids = fields.Many2many(
        comodel_name="res.city", relation="res_company_ocd_express_city_rel", column1="company_id",
        column2="city_id", string="Cities Open To OCD Express",
        help="Where OCD Express picks up and delivers with its couriers (the rate « OCD courier » of the "
        "city gives the price). Towards another city: by travel agency, paid in advance.",
    )
    ocd_express_cod_rate = fields.Float(string="Collecting At The Door (%)", default=1.5)
    ocd_express_cod_min = fields.Monetary(string="Collecting At The Door, At Least", default=150)
    ocd_express_return_fee = fields.Monetary(string="Price Of A Return", default=500)
    ocd_express_pickup_fee = fields.Monetary(string="Price Of A Small Pick-Up", default=500)
    ocd_express_pickup_free_from = fields.Integer(
        string="Free Pick-Up From", default=3,
        help="Parcels taken in the same passage. Below, the pick-up is paid; the drop-off at the OCD point is free.",
    )
    ocd_express_cap_new = fields.Monetary(string="To Collect At Most (New Sender)", default=50000)
    ocd_express_cap_confirmed = fields.Monetary(string="To Collect At Most (Confirmed Sender)", default=200000)
    ocd_express_cap_after = fields.Integer(
        string="Parcels Delivered To Be Confirmed", default=20,
        help="Delivered without a problem reported by the customer.",
    )
    ocd_express_online_above = fields.Monetary(
        string="On The Phone Only Above", default=100000,
        help="Above this amount, the customer pays on their phone, never in cash. 0: never.",
    )
    ocd_express_cash_max = fields.Monetary(
        string="Cash On A Courier At Most", default=150000,
        help="Above, the courier drops the cash at the OCD point before collecting more in cash. 0: no limit.",
    )
    ocd_express_debt_max = fields.Monetary(
        string="Owed By A Sender At Most", default=10000,
        help="Above, the sender pays what they owe before a new parcel, or the customer pays the delivery.",
    )
    ocd_express_id_daily = fields.Monetary(
        string="Identity Checked Above (A Day)", default=300000,
        help="Money to collect in one day by a sender whose identity the team did not check: the parcels "
        "above wait for the team. 0: never.",
    )
    ocd_express_first_day_max = fields.Integer(
        string="Parcels Of The First Day Before A Check", default=10,
        help="A new sender who sends more parcels on their first day: the next ones wait for the team. 0: never.",
    )
    ocd_express_wave1_hour = fields.Float(
        string="Morning Wave Before", default=10.0,
        help="A parcel created before this hour is picked up in the morning and delivered in the afternoon.",
    )
    ocd_express_wave2_hour = fields.Float(
        string="Afternoon Wave Before", default=15.0,
        help="A parcel created before this hour is picked up in the afternoon and delivered the next morning. "
        "Later: picked up the next morning.",
    )
    ocd_express_per_courier = fields.Integer(
        string="Parcels Per Courier And Per Day", default=20, help="Pick-ups included. 0: no limit.",
    )
    ocd_express_shop_share = fields.Float(
        string="Share Kept For The Shop (%)", default=20,
        help="Of the capacity of the couriers: kept for the parcels of the shop.",
    )
    ocd_express_claim_hours = fields.Integer(
        string="Problem Reported Within (Hours)", default=48,
        help="After the delivery, the customer reports a problem from their page: the money of the parcel waits.",
    )
    ocd_express_lost_max = fields.Monetary(string="Lost Or Damaged: Paid At Most", default=50000)
    ocd_express_return_alert = fields.Float(
        string="Returns Of A Sender: Alert At (%)", default=30,
        help="On the last 30 days, from 10 parcels: a warning, then the suspension. 0: never.",
    )
    ocd_express_momo_hold_hours = fields.Integer(
        string="New Payout Number: Wait (Hours)", default=48,
        help="The first payout towards a new Mobile Money number waits; the old number is told.",
    )
    ocd_express_retention_months = fields.Integer(
        string="Customers Erased After (Months)", default=6,
        help="The name, the number and the address of the customers of OCD Express; the amounts and the "
        "dates stay for the accounts. 0: never.",
    )
    ocd_express_point = fields.Char(
        string="OCD Point", help="Where the senders drop their parcels and the couriers their cash (the studio).",
    )
    ocd_express_momo_number = fields.Char(
        string="Mobile Money Of OCD", help="Where a sender sends what they owe, with the reference given on their page.",
    )

    # === DAYS AND WAVES === #

    def _ocd_express_working_day(self, day):
        """Monday to Saturday: the couriers do not pick up on Sunday."""
        return day.weekday() != 6

    def _ocd_express_next_working_day(self, day):
        day += timedelta(days=1)
        while not self._ocd_express_working_day(day):
            day += timedelta(days=1)
        return day

    def _ocd_express_slot(self, moment=None):
        """(pick-up day, pick-up part, delivery day, delivery part) of a parcel created at `moment`
        (naive UTC, now by default), in the days of the studio."""
        self.ensure_one()
        local = self._ocd_to_local(moment or fields.Datetime.now())
        day, hour = local.date(), local.hour + local.minute / 60
        if not self._ocd_express_working_day(day):
            day, hour = self._ocd_express_next_working_day(day), 0.0
        if hour < self.ocd_express_wave1_hour:
            return day, "morning", day, "afternoon"
        if hour < self.ocd_express_wave2_hour:
            return day, "afternoon", self._ocd_express_next_working_day(day), "morning"
        following = self._ocd_express_next_working_day(day)
        return following, "morning", following, "afternoon"

    def _ocd_express_next_slot(self, day, part):
        """The pick-up slot after (`day`, `part`): (pick-up day, part, delivery day, part)."""
        self.ensure_one()
        if part == "morning":
            return day, "afternoon", self._ocd_express_next_working_day(day), "morning"
        following = self._ocd_express_next_working_day(day)
        return following, "morning", following, "afternoon"

    def _ocd_express_part_start(self, day, part):
        """The start (naive UTC) of the part of `day` of the studio."""
        self.ensure_one()
        hour = {"morning": 8.0, "afternoon": self.ocd_express_wave1_hour + 2, "evening": 17.0}[part]
        local = self._ocd_tz().localize(datetime.combine(day, time()) + timedelta(hours=hour))
        return self._ocd_to_utc(local)

    # === CAPACITY === #

    def _ocd_express_capacity(self):
        """Parcels of OCD Express the couriers deliver in a day: the couriers × the parcels per
        courier, minus the share kept for the shop. None: no limit."""
        self.ensure_one()
        if not self.ocd_express_per_courier:
            return None
        couriers = self.env["res.partner"].sudo().search_count([("ocd_is_courier", "=", True)])
        share = 1 - min(max(self.ocd_express_shop_share, 0.0), 100.0) / 100
        return int(max(couriers, 1) * self.ocd_express_per_courier * share)

    def _ocd_express_load(self, day):
        """Parcels of OCD Express to deliver on `day`."""
        self.ensure_one()
        return self.env["stock.picking"].sudo().search_count([
            ("ocd_express", "=", True),
            ("company_id", "=", self.id),
            ("ocd_express_deliver_on", "=", day),
            ("ocd_stage", "not in", ("cancelled", "returned", "delivered")),
        ])

    def _ocd_express_plan(self, moment=None, count=1):
        """The first slot (pick-up day, part, delivery day, part) after `moment` with room for
        `count` parcels."""
        self.ensure_one()
        slot = self._ocd_express_slot(moment)
        capacity = self._ocd_express_capacity()
        if capacity is None:
            return slot
        for _attempt in range(14):
            if self._ocd_express_load(slot[2]) + count <= capacity:
                return slot
            slot = self._ocd_express_next_slot(slot[0], slot[1])
        return slot

    # === MONEY === #

    def _ocd_express_cod_fee(self, amount):
        """The share of OCD for collecting `amount` at the door for a sender."""
        self.ensure_one()
        currency = self.currency_id
        if currency.compare_amounts(amount, 0.0) <= 0:
            return 0.0
        fee = max(amount * self.ocd_express_cod_rate / 100, self.ocd_express_cod_min)
        return currency.round(min(fee, amount))
