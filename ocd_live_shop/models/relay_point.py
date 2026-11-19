"""Relay points (chantier 10, design PointsRelais).

A relay point is a place (`ocd.vendor.place`, chantier 17) that keeps the parcels of the customers
who chose it: a shop of the neighbourhood held by a partner of OCD Live (a contact « holds a relay
point »), or the verified store of a vendor who wants it (A.6 of the plan of « My products »).

The customer chooses « At a relay point » at the delivery step: one relay point for the whole
order, cheaper than at the door (the rates « relay point » of OCD Live), only for the parcels
carried by the OCD couriers in the city of the relay point. The courier of its district takes the
parcels there; the relay point counts each parcel it receives, one by one (a parcel damaged stays
with the courier). The customer is told, with the day it waits until (7 days), and picks it up with
their code; paid before, or on their phone at the counter: never in cash, a relay point keeps no
money. Not picked up in time: a reminder before, then the parcel goes back (refunded when paid
online; OCD Express: back to its sender against their return code) and the courier takes it back.

The relay point earns a fixed amount per parcel handed over (a bill, in the payouts, every month for
the partners); a parcel lost there is paid back by OCD and taken from its earnings, and after the
losses of the settings the relay point is paused for the team. A full relay point, on holiday or
closed is not offered; the parcels it keeps wait for their customers."""
import re
from datetime import datetime, time, timedelta

import pytz

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import consteq

from odoo.addons.ocd_live import tools

ACTIVITY_REFUND = "ocd_live_shop.mail_activity_type_refund"
ACTIVITY_PROBLEM = "ocd_live_shop.mail_activity_type_parcel_problem"
RELAY_MOVE_KINDS = [("earning", "Parcel handed over"), ("loss", "Parcel lost at the relay point")]
# The parcels kept by a relay point: waiting for their customer, or for the courier to take back
HELD = ["|", ("ocd_stage", "=", "at_relay"), ("ocd_relay_back", "=", True)]
NAME_MAX = 80
NOTE_MAX = 300


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_relay_enabled = fields.Boolean(
        string="Relay Points",
        default=True,
        help="The customers may choose a relay point at the delivery step, where the relay points are open.",
    )
    ocd_relay_fee = fields.Monetary(
        string="Earned By A Relay Point Per Parcel",
        default=150,
        help="For each parcel handed over to its customer; nothing for a parcel taken back.",
    )
    ocd_relay_days = fields.Integer(
        string="Days Kept At A Relay Point",
        default=7,
        help="A parcel waits so many days for its customer (until the closing of the relay point on the last "
        "day), then it goes back.",
    )
    ocd_relay_reminder_days = fields.Integer(
        string="Reminder Before The End (Days)", default=2, help="0: no reminder.",
    )
    ocd_relay_capacity = fields.Integer(
        string="Places Of A Relay Point",
        default=25,
        help="Parcels a relay point keeps at most, by default: full, it is not offered.",
    )
    ocd_relay_vendor_stores = fields.Boolean(
        string="Stores Of The Vendors As Relay Points",
        default=True,
        help="A vendor whose store is verified and open to the public may keep the parcels of the others.",
    )
    ocd_relay_pause_after = fields.Integer(
        string="Paused After (Parcels Lost)",
        default=2,
        help="A relay point that lost so many parcels is paused until the team checks it. 0: never.",
    )


class ResPartner(models.Model):
    _inherit = "res.partner"

    ocd_is_relay = fields.Boolean(
        string="Holds A Relay Point",
        index="btree_not_null",
        tracking=True,
        help="A partner of OCD Live who keeps the parcels in their shop (not a vendor).",
    )

    def _ocd_relay_places(self):
        """The relay points held by this contact (their shop, or the stores of a vendor)."""
        self.ensure_one()
        return self.env["ocd.vendor.place"].sudo().search([("vendor_id", "=", self.id), ("relay", "=", True)])

    @api.model
    def _ocd_find_relay_by_phone(self, phone):
        """The holder of a relay point whose number ends like `phone`, for the login page."""
        holder = self._ocd_find_by_phone(phone, [("ocd_is_relay", "=", True)])
        if holder:
            return holder
        vendors = self._ocd_find_by_phone(phone, [("ocd_is_vendor", "=", True)])
        return vendors if vendors and vendors._ocd_relay_places() else self.browse()


class OcdVendorPlace(models.Model):
    _inherit = "ocd.vendor.place"

    relay = fields.Boolean(
        string="Relay Point",
        index="btree_not_null",
        tracking=True,
        help="The place keeps the parcels of the customers who chose it, for OCD Live.",
    )
    relay_capacity = fields.Integer(
        string="Places", default=lambda self: self.env.company.ocd_relay_capacity,
        help="Parcels it keeps at most: full, it is not offered.",
    )
    relay_open = fields.Boolean(
        string="Receives Parcels",
        default=True,
        tracking=True,
        help="Off: no new parcel (on holiday, or paused by the team); the parcels it keeps wait for their customers.",
    )
    relay_pause_note = fields.Char(string="Why It Is Paused", tracking=True)
    relay_id_checked = fields.Boolean(string="Identity Checked", tracking=True)
    relay_visited = fields.Boolean(string="Visited By The Team", tracking=True)
    relay_business = fields.Char(string="What The Shop Sells")
    relay_held_count = fields.Integer(string="Kept", compute="_compute_relay_counts")
    relay_coming_count = fields.Integer(string="On The Way", compute="_compute_relay_counts")
    relay_back_count = fields.Integer(string="To Take Back", compute="_compute_relay_counts")
    relay_given_count = fields.Integer(string="Handed Over (30 Days)", compute="_compute_relay_counts")
    relay_lost_count = fields.Integer(string="Lost", compute="_compute_relay_counts")
    relay_month_amount = fields.Monetary(
        string="Earned This Month", compute="_compute_relay_counts", currency_field="relay_currency_id",
    )
    relay_currency_id = fields.Many2one(related="company_id.currency_id", string="Currency")
    relay_holder_kind = fields.Selection(
        selection=[("partner", "Partner"), ("vendor", "Vendor")], string="Held By",
        compute="_compute_relay_holder_kind",
    )

    @api.depends("vendor_id.ocd_is_vendor")
    def _compute_relay_holder_kind(self):
        for place in self:
            place.relay_holder_kind = "vendor" if place.vendor_id.ocd_is_vendor else "partner"

    def _compute_relay_counts(self):
        Picking = self.env["stock.picking"].sudo()
        Move = self.env["account.move"].sudo()
        since = fields.Datetime.now() - timedelta(days=30)
        month_start = self.env.company._ocd_local_today().replace(day=1)
        domain = [("ocd_is_parcel", "=", True), ("ocd_relay_id", "in", self.ids)]

        def counts(extra):
            return dict(Picking._read_group(domain + extra, ["ocd_relay_id"], ["__count"]))

        held = counts(HELD)
        coming = counts([("ocd_stage", "=", "on_the_way")])
        back = counts([("ocd_relay_back", "=", True)])
        given = counts([("ocd_stage", "=", "delivered"), ("ocd_delivered_at", ">=", since)])
        lost = counts([("ocd_relay_lost", "=", True)])
        amounts = {}
        for move in Move.search([
            ("ocd_relay_kind", "!=", False), ("state", "=", "posted"), ("invoice_date", ">=", month_start),
            ("ocd_picking_id.ocd_relay_id", "in", self.ids),
        ]):
            sign = 1 if move.move_type == "in_invoice" else -1
            key = move.ocd_picking_id.ocd_relay_id.id
            amounts[key] = amounts.get(key, 0.0) + sign * move.amount_total
        for place in self:
            key = place._origin or place
            place.relay_held_count = held.get(key, 0)
            place.relay_coming_count = coming.get(key, 0)
            place.relay_back_count = back.get(key, 0)
            place.relay_given_count = given.get(key, 0)
            place.relay_lost_count = lost.get(key, 0)
            place.relay_month_amount = amounts.get(key.id, 0.0)

    # === WHERE THE CUSTOMERS MAY PICK UP === #

    def _ocd_relay_available(self, day=None):
        """Whether a customer may choose this relay point now: online, receiving parcels, open
        (not closed on `day`), with a free place."""
        self.ensure_one()
        company = self.company_id
        day = day or company._ocd_local_today()
        # Counted now: a parcel may have left or arrived in the same transaction
        self.invalidate_recordset(["relay_held_count", "relay_coming_count"])
        return bool(
            company.ocd_relay_enabled and self.active and self.relay and self.relay_open
            and self.state == "approved" and self.kind == "store"
            and not (self.closed_until and self.closed_until >= day)
            and (self.relay_holder_kind == "partner" or company.ocd_relay_vendor_stores)
            and self.relay_held_count + self.relay_coming_count < (self.relay_capacity or company.ocd_relay_capacity)
        )

    @api.model
    def _ocd_relay_points(self, city, district=None, company=None):
        """The relay points a customer may choose in `city`: the ones of `district` first, then the
        others by name."""
        company = company or self.env.company
        if not city or not company.ocd_relay_enabled:
            return self.browse()
        places = self.sudo().search([
            ("relay", "=", True), ("state", "=", "approved"), ("kind", "=", "store"), ("company_id", "=", company.id),
            "|", ("city_id", "=", city.id), ("district_id.city_id", "=", city.id),
        ]).filtered(lambda place: place._ocd_relay_available())
        return places.sorted(lambda place: (not district or place.district_id != district, place.name or ""))

    def _ocd_month_start_utc(self):
        """The start of the month at the relay point (naive UTC)."""
        self.ensure_one()
        tz = self._ocd_tz()
        today = fields.Datetime.now().replace(tzinfo=pytz.utc).astimezone(tz).date()
        start = tz.localize(datetime.combine(today.replace(day=1), time()))
        return start.astimezone(pytz.utc).replace(tzinfo=None)

    def _ocd_relay_line(self):
        """« Akwa · Rue Joss, face à la boulangerie · Ouvert · ferme à 20:00 »."""
        self.ensure_one()
        return " · ".join(part for part in (self._ocd_address_line(), self._ocd_open_state()["label"]) if part)

    # === THE RELAY POINT AT WORK === #

    def _ocd_relay_parcels(self, which):
        """The parcels of the relay point: « coming » (on the way with the courier), « held »
        (waiting for their customer), « back » (not picked up, waiting for the courier)."""
        self.ensure_one()
        domain = [("ocd_is_parcel", "=", True), ("ocd_relay_id", "=", self.id)]
        extra = {
            "coming": [("ocd_stage", "=", "on_the_way")],
            "held": [("ocd_stage", "=", "at_relay")],
            "back": [("ocd_relay_back", "=", True)],
        }[which]
        order = "ocd_relay_deadline, id" if which == "held" else "id"
        return self.env["stock.picking"].sudo().search(domain + extra, order=order)

    def _ocd_relay_receive(self, parcels, refused=None):
        """The relay point counted `parcels` brought by the courier: they wait for their customer
        (told on WhatsApp, with the day they wait until). `refused`: {parcel: note} damaged or
        open, they stay with the courier as a problem. Return the parcels received."""
        self.ensure_one()
        refused = refused or {}
        now = fields.Datetime.now()
        received = self.env["stock.picking"].sudo()
        for parcel in parcels.sudo():
            if parcel.ocd_relay_id != self or parcel.ocd_stage != "on_the_way":
                raise UserError(self.env._("The parcel %s is not on its way to this relay point.", parcel.name))
            if parcel in refused:
                note = refused[parcel] or self.env._("Damaged or open")
                parcel._ocd_report_problem("damaged", self.env._("Refused by the relay point %(relay)s: %(note)s",
                                                                 relay=self.name, note=note))
                continue
            values = {
                "ocd_stage": "at_relay",
                "ocd_relay_received_at": now,
                "ocd_relay_deadline": parcel._ocd_relay_deadline_from(now),
                "ocd_relay_reminded_at": False,
                "ocd_code_sent_at": now,
            }
            if not parcel.ocd_delivery_code:
                values.update({"ocd_delivery_code": parcel._ocd_new_code(), "ocd_code_attempts": 0})
            parcel.write(values)
            parcel.message_post(body=self.env._("Received by the relay point %s.", self.name))
            parcel._ocd_relay_notify("relay_arrived")
            received |= parcel
        return received

    def _ocd_relay_hand_over(self, parcel, code):
        """The customer gives their code at the counter. Return (handed over, attempts left)."""
        self.ensure_one()
        parcel = parcel.sudo()
        if parcel.ocd_relay_id != self or parcel.ocd_stage != "at_relay":
            raise UserError(self.env._("The parcel %s is not kept by this relay point.", parcel.name))
        return parcel._ocd_check_code(code)

    def _ocd_relay_parcel_by_qr(self, text):
        """The parcel of the QR shown by the customer (« OCD-<parcel>-<code> »), with its code."""
        self.ensure_one()
        match = re.fullmatch(r"OCD-(\d+)-(\d{4})", (text or "").strip())
        if not match:
            return self.env["stock.picking"], ""
        parcel = self.env["stock.picking"].sudo().browse(int(match.group(1))).exists()
        if not parcel or parcel.ocd_relay_id != self or parcel.ocd_stage != "at_relay":
            return self.env["stock.picking"], ""
        return parcel, match.group(2)

    def _ocd_relay_set_open(self, receives):
        """The holder of the relay point stops or starts receiving parcels (holiday). A relay
        point paused by the team opens again only by the team."""
        self.ensure_one()
        if receives and self.relay_pause_note:
            raise UserError(self.env._("The team of OCD Live paused your relay point: call them to open it again."))
        self.sudo().write({"relay_open": bool(receives)})
        return True

    def _ocd_relay_notify_incoming(self, parcels):
        """Tell the relay point the parcels a courier brings (extended by ocd_live_shop_whatsapp)."""

    def _ocd_relay_incoming_count(self):
        """The parcels on the way to the relay point, for its message (context of the template)."""
        self.ensure_one()
        return self.env.context.get("ocd_relay_count") or self.relay_coming_count

    # === THE TEAM === #

    def _ocd_relay_check_team(self):
        if not self.env.user.has_group("ocd_live.group_ocd_live_user"):
            raise AccessError(self.env._("Only the team of OCD Live manages the relay points."))

    def action_ocd_relay_pause(self, note=None):
        self._ocd_relay_check_team()
        self.write({"relay_open": False, "relay_pause_note": note or self.env._("Paused by the team")})
        return True

    def action_ocd_relay_resume(self):
        self._ocd_relay_check_team()
        self.write({"relay_open": True, "relay_pause_note": False})
        return True

    def action_ocd_relay_parcels(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Parcels of the relay point %s", self.name),
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("ocd_relay_id", "=", self.id)],
            "context": {"create": False},
        }

    def _ocd_relay_check_losses(self):
        """Paused after the losses of the settings, until the team checks it."""
        for place in self:
            limit = place.company_id.ocd_relay_pause_after
            if limit and place.relay_open and place.relay_lost_count >= limit:
                place.sudo().write({
                    "relay_open": False,
                    "relay_pause_note": self.env._("%s parcels lost: to check by the team", place.relay_lost_count),
                })
                place._ocd_relay_alert(self.env._(
                    "%(count)s parcels lost at the relay point %(relay)s: it receives no new parcel until the team "
                    "checks it.", count=place.relay_lost_count, relay=place.name))

    def _ocd_relay_alert(self, body):
        """Alert the team: the channel of the deliveries, the history of the relay point and an
        activity on the one who holds it."""
        self.ensure_one()
        channel = self.company_id.ocd_deliveries_channel_id
        if channel:
            channel.sudo().message_post(body=body, message_type="comment", subtype_xmlid="mail.mt_comment")
        self.sudo().message_post(body=body)
        user = self.company_id.ocd_live_responsible_id or self.env.ref("base.user_admin", raise_if_not_found=False)
        self.vendor_id.sudo().activity_schedule("mail.mail_activity_data_todo", note=body,
                                                summary=self.env._("Relay point %s", self.name),
                                                user_id=user.id if user else self.env.uid)

    # === BECOME A RELAY POINT === #

    @api.model
    def _ocd_relay_request(self, shop, holder, phone, country, district, landmark, business):
        """A shop asks to become a relay point (/points-relais): its holder (a contact who holds
        a relay point, or the one known for this number) and its place, checked by the team
        (visit, identity, front). Return the place."""
        _ = self.env._
        shop = (shop or "").strip()[:NAME_MAX]
        holder_name = (holder or "").strip()[:NAME_MAX]
        if not shop or not holder_name:
            raise UserError(_("Write the name of the shop and your name."))
        if not district:
            raise UserError(_("Choose the district of the shop."))
        Partner = self.env["res.partner"].sudo()
        partner = Partner._ocd_find_by_phone(phone, [("ocd_is_relay", "=", True)])
        if not partner:
            partner = Partner.create({
                "name": holder_name, "phone": phone, "country_id": country.id if country else False,
                "city_id": district.city_id.id, "district_id": district.id, "ocd_is_relay": True,
                "ocd_payout_frequency": "monthly", "ocd_payout_momo": phone,
            })
        place = self.sudo().create({
            "name": shop,
            "vendor_id": partner.id,
            "kind": "store",
            "city_id": district.city_id.id,
            "district_id": district.id,
            "landmark": (landmark or "").strip()[:200] or False,
            "phone": phone,
            "relay": True,
            "relay_business": (business or "").strip()[:NOTE_MAX] or False,
            "state": "to_check",
        })
        place._ocd_relay_alert(_("%(shop)s (%(district)s) asks to become a relay point: visit it.",
                                 shop=shop, district=district.name))
        return place


class OcdDeliveryRate(models.Model):
    _inherit = "ocd.delivery.rate"

    @api.model
    def _ocd_relay_quote(self, vendor, relay, goods_amount, currency, company, date=None, rates=None, quantities=None):
        """The delivery of the parcel of `vendor` to the relay point `relay`: the rate « relay point »
        of OCD Live from the city of the parcel to the relay point, for the parcels carried by the
        OCD couriers in that city."""
        _ = self.env._
        rates = rates if rates is not None else self._ocd_rates(company)
        probe = self.env["res.partner"].new({
            "country_id": (relay.country_id or relay.city_id.country_id).id, "city_id": relay.city_id.id,
            "district_id": relay.district_id.id,
        })
        origin = self._ocd_origin(vendor, company, probe, quantities)
        quote = {
            "vendor": vendor, "rate": self.browse(), "operator": "relay", "origin": origin[1], "price": 0.0,
            "allow_cod": True, "description": _("At the relay point %s", relay.name), "error": False,
            "relay": relay,
        }
        mode = (vendor.ocd_delivery_mode or company.ocd_default_delivery_mode) if vendor else "stock"
        city = relay.city_id or relay.district_id.city_id
        if vendor and mode == "vendor":
            quote["error"] = _("%s delivers their parcels: not at a relay point.", vendor.name)
            return quote
        if not origin[1] or origin[1] != city:
            quote["error"] = _("%(name)s sends from %(city)s: not at a relay point of %(relay_city)s.",
                               name=vendor.name if vendor else "OCD Live", city=origin[1].name or "-",
                               relay_city=city.name or "-")
            return quote
        rate = rates.filtered(lambda r: not r.vendor_id and r.operator == "relay")._ocd_best(probe, origin)
        if not rate:
            quote["error"] = _("No price of the relay points in %s yet.", city.name or "-")
            return quote
        quote.update({"rate": rate, "price": rate._ocd_price(goods_amount, currency, company, date),
                      "allow_cod": bool(rate.allow_cod)})
        return quote


class OcdOrderDelivery(models.Model):
    _inherit = "ocd.order.delivery"

    relay_place_id = fields.Many2one(
        comodel_name="ocd.vendor.place", string="Relay Point", ondelete="set null",
        help="The relay point where the customer picks the parcel up.",
    )


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ocd_relay_id = fields.Many2one(
        comodel_name="ocd.vendor.place", string="Relay Point", copy=False, ondelete="set null",
        help="The relay point where the customer picks up the parcels of the order.",
    )

    def _ocd_relay_points(self, city, district=None):
        """The relay points the customer may choose for the whole order in `city`: every parcel
        carried there by the OCD couriers, at the price of the relay points."""
        self.ensure_one()
        relays = self.env["ocd.vendor.place"]._ocd_relay_points(city, district, self.company_id)
        if not relays or not self._ocd_delivery_groups():
            return relays.browse()
        first = relays[:1]
        quotes = self._ocd_delivery_quotes(relay=first)
        if any(quote["error"] for quote in quotes):
            return relays.browse()
        return relays

    def _ocd_set_relay(self, relay):
        """The relay point chosen by the customer (empty: delivered or picked up in a store)."""
        self.ensure_one()
        if relay:
            if not relay._ocd_relay_available():
                raise UserError(self.env._("The relay point %s does not take new parcels now: choose another one.",
                                           relay.name))
            errors = [quote["error"] for quote in self._ocd_delivery_quotes(relay=relay) if quote["error"]]
            if errors:
                raise UserError(" ".join(errors))
            self.sudo().write({"ocd_relay_id": relay.id, "ocd_collect_place_ids": [Command.clear()]})
        elif self.ocd_relay_id:
            self.sudo().ocd_relay_id = False
        return True

    def _needs_customer_address(self):
        """Override: picked up at a relay point, the customer gives their name and their WhatsApp."""
        if len(self) == 1 and self.ocd_relay_id:
            return False
        return super()._needs_customer_address()


class ResPartnerAddress(models.Model):
    _inherit = "res.partner"

    def _get_mandatory_address_fields(self, country_sudo, **kwargs):
        """Override: an order picked up at a relay point asks no address."""
        order = kwargs.get("order_sudo")
        if order and len(order) == 1 and order.ocd_relay_id:
            return set()
        return super()._get_mandatory_address_fields(country_sudo, **kwargs)


class AccountMove(models.Model):
    _inherit = "account.move"

    ocd_relay_kind = fields.Selection(selection=RELAY_MOVE_KINDS, string="Relay Point", copy=False, readonly=True)


class OcdPayout(models.Model):
    _inherit = "ocd.payout"

    @api.model
    def _ocd_may_pay(self, vendor, net, company, force=False):
        """A relay point that owes OCD (a parcel lost) waits for its next earnings."""
        if vendor.ocd_is_relay and not vendor.ocd_is_vendor and not force \
                and company.currency_id.compare_amounts(net, 0.0) <= 0:
            return False
        return super()._ocd_may_pay(vendor, net, company, force=force)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ocd_relay_id = fields.Many2one(
        comodel_name="ocd.vendor.place", string="Relay Point", copy=False, index="btree_not_null",
        ondelete="restrict", help="The relay point where the customer picks the parcel up.",
    )
    ocd_relay_received_at = fields.Datetime(string="Received By The Relay Point", copy=False)
    ocd_relay_deadline = fields.Datetime(string="Kept Until", copy=False)
    ocd_relay_reminded_at = fields.Datetime(string="Customer Reminded At", copy=False)
    ocd_relay_back = fields.Boolean(
        string="To Take Back From The Relay Point", copy=False, index="btree_not_null",
        help="Not picked up in time: it waits at the relay point for the courier.",
    )
    ocd_relay_taken_back_at = fields.Datetime(string="Taken Back At", copy=False)
    ocd_relay_lost = fields.Boolean(string="Lost At The Relay Point", copy=False, tracking=True)

    def _ocd_relay_deadline_from(self, start):
        """The end of the wait at the relay point: its closing on the day so many days later (the
        setting), else on its next day open; the end of that day without hours."""
        self.ensure_one()
        relay = self.ocd_relay_id
        days = max(self.company_id.ocd_relay_days or 7, 1)
        tz = relay._ocd_tz()
        day = pytz.utc.localize(start).astimezone(tz).date() + timedelta(days=days)
        intervals = relay._ocd_intervals()
        closing = None
        for offset in range(8):
            candidate = day + timedelta(days=offset)
            if relay.closed_until and candidate <= relay.closed_until:
                continue
            hours = intervals.get(candidate.weekday()) if intervals else None
            if hours:
                closing = tz.localize(datetime.combine(candidate, time()) + timedelta(hours=max(end for _s, end in hours)))
                break
        if closing is None:
            closing = tz.localize(datetime.combine(day, time(23, 59)))
        return closing.astimezone(pytz.utc).replace(tzinfo=None)

    def _ocd_relay_deadline_text(self, lang=None):
        """« mardi 1er décembre à 20:00 », at the hour of the relay point; in `lang` when it is
        installed (the language of a WhatsApp template)."""
        self.ensure_one()
        if lang and lang != self.env.lang and self.env["res.lang"]._ocd_is_active(lang):
            return self.with_context(lang=lang)._ocd_relay_deadline_text()
        if not self.ocd_relay_deadline:
            return ""
        local = pytz.utc.localize(self.ocd_relay_deadline).astimezone(self.ocd_relay_id._ocd_tz())
        return self.env._("%(day)s at %(hour)s", day=tools.day_text(self.env, local.date(), "EEEE d MMMM"),
                          hour=local.strftime("%H:%M"))

    def _ocd_relay_qr_text(self):
        """What the QR of the customer says at the counter: the parcel and its code."""
        self.ensure_one()
        return f"OCD-{self.id}-{self.sudo().ocd_delivery_code or ''}"

    def _ocd_relay_notify(self, event):
        """Tell the customer about their parcel at the relay point: arrived, reminder, gone back
        (extended by the WhatsApp modules)."""

    def action_ocd_leave(self):
        """Override: the relay point is told the parcels its courier brings, once per relay
        point; the customer is told when the relay point has counted their parcel."""
        result = super().action_ocd_leave()
        for relay, parcels in self.filtered("ocd_relay_id").grouped("ocd_relay_id").items():
            relay.with_context(ocd_relay_count=len(parcels))._ocd_relay_notify_incoming(parcels)
        return result

    def _ocd_deliver(self):
        """Override: a parcel handed over at a relay point is a parcel earned by the relay point."""
        result = super()._ocd_deliver()
        self.filtered(lambda p: p.ocd_relay_id and p.ocd_stage == "delivered")._ocd_relay_earn()
        return result

    def _ocd_relay_move(self, kind, amount, label):
        """A bill (earned) or a credit note (lost) of the holder of the relay point of the parcel."""
        self.ensure_one()
        company = self.company_id
        holder = self.ocd_relay_id.vendor_id
        product = self.env.ref("ocd_live_shop.product_relay_earning" if kind == "earning"
                               else "ocd_live_shop.product_relay_loss").product_variant_id
        move = self.env["account.move"].sudo().create({
            "move_type": "in_invoice" if kind == "earning" else "in_refund",
            "partner_id": holder.id,
            "company_id": company.id,
            "currency_id": company.currency_id.id,
            "invoice_date": fields.Date.context_today(self),
            "ref": self.name,
            "invoice_origin": self.name,
            "ocd_picking_id": self.id,
            "ocd_relay_kind": kind,
            "invoice_line_ids": [Command.create({
                "product_id": product.id, "name": label, "quantity": 1, "price_unit": amount,
                "tax_ids": [Command.clear()],
            })],
        })
        move.action_post()
        return move

    def _ocd_relay_earn(self):
        """The fixed amount of the settings for each parcel handed over, once per parcel."""
        for parcel in self.sudo():
            fee = parcel.company_id.ocd_relay_fee
            if parcel.company_id.currency_id.compare_amounts(fee, 0.0) <= 0:
                continue
            if parcel.ocd_vendor_bill_ids.filtered(lambda m: m.ocd_relay_kind == "earning"):
                continue
            parcel._ocd_relay_move("earning", fee, self.env._("Parcel %s handed over", parcel.name))

    @api.model
    def _cron_ocd_relay(self):
        """The parcels at the relay points: a reminder before the end, then they go back."""
        now = fields.Datetime.now()
        for parcel in self.sudo().search([("ocd_is_parcel", "=", True), ("ocd_stage", "=", "at_relay"),
                                          ("ocd_relay_deadline", "!=", False)]):
            days = parcel.company_id.ocd_relay_reminder_days
            if parcel.ocd_relay_deadline <= now:
                parcel._ocd_relay_expire()
            elif days and not parcel.ocd_relay_reminded_at and parcel.ocd_relay_deadline - timedelta(days=days) <= now:
                parcel.ocd_relay_reminded_at = now
                parcel._ocd_relay_notify("relay_reminder")

    def _ocd_relay_expire(self):
        """Not picked up in time: it goes back (refunded when paid online), and waits at the relay
        point for the courier, who takes it back with his next passage."""
        for parcel in self:
            parcel.message_post(body=self.env._("Not picked up before %s: the parcel goes back.",
                                                parcel._ocd_relay_deadline_text()))
            parcel.write({"ocd_relay_back": True, "ocd_courier_id": parcel.ocd_courier_id.id or
                          self.env["res.partner"]._ocd_find_courier(parcel.ocd_relay_id.district_id).id})
            parcel._ocd_return(event="relay_expired")
        return True

    def _ocd_relay_take_back(self, courier):
        """The courier took the parcels not picked up at the relay point back."""
        for parcel in self.sudo():
            if not parcel.ocd_relay_back:
                raise UserError(self.env._("The parcel %s is not to take back.", parcel.name))
            parcel.write({"ocd_relay_back": False, "ocd_relay_taken_back_at": fields.Datetime.now(),
                          "ocd_courier_id": courier.id})
            parcel.message_post(body=self.env._("Taken back from the relay point %(relay)s by %(courier)s.",
                                                relay=parcel.ocd_relay_id.name, courier=courier.name))
        return True

    def _ocd_relay_lost_value(self):
        """What OCD pays back for a parcel lost at a relay point (extended by OCD Express)."""
        self.ensure_one()
        return self.ocd_goods_amount + self.ocd_fee_amount

    def action_ocd_relay_lost(self):
        """Lost at the relay point: OCD pays it back (the customer, refunded by the team), and
        takes it from the earnings of the relay point; paused after the losses of the settings."""
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only a manager of OCD Live records a parcel lost at a relay point."))
        for parcel in self.sudo():
            relay = parcel.ocd_relay_id
            if not relay or parcel.ocd_relay_lost:
                continue
            if parcel.ocd_stage != "at_relay" and not parcel.ocd_relay_back:
                raise UserError(self.env._("The parcel %s is not at the relay point.", parcel.name))
            value = parcel._ocd_relay_lost_value()
            parcel.write({"ocd_relay_lost": True, "ocd_relay_back": False})
            if parcel.company_id.currency_id.compare_amounts(value, 0.0) > 0:
                parcel._ocd_relay_move("loss", value, self.env._("Parcel %s lost at the relay point", parcel.name))
            parcel._ocd_relay_lost_paid_back(value)
            relay._ocd_relay_check_losses()
        return True

    def _ocd_relay_lost_paid_back(self, value):
        """OCD pays the parcel back: the team refunds the customer and pays the vendor their share
        (extended by OCD Express: the sender is paid back)."""
        self.ensure_one()
        if self.ocd_stage not in ("returned", "cancelled"):
            self.write({"ocd_stage": "cancelled"})
            if self.state not in ("done", "cancel"):
                self.action_cancel()
        self._ocd_alert(self.env._(
            "The parcel %(parcel)s is lost at the relay point %(relay)s: pay back %(amount)s to the customer "
            "and its share to %(vendor)s.", parcel=self.name, relay=self.ocd_relay_id.name,
            amount=value, vendor=self.ocd_vendor_id.name or "OCD Live"), ACTIVITY_REFUND)

    def _ocd_return(self, event="returned"):
        """Override: a parcel kept by a relay point stays at the relay point until the courier
        takes it back (the stage says it goes back)."""
        at_relay = self.filtered(lambda p: p.ocd_stage == "at_relay")
        at_relay.write({"ocd_relay_back": True})
        return super()._ocd_return(event)

    def _ocd_relay_check_code(self, code):
        """The code typed at the counter (constant time)."""
        self.ensure_one()
        expected = self.sudo().ocd_delivery_code or ""
        return bool(expected and code and consteq(expected, (code or "").strip()))
