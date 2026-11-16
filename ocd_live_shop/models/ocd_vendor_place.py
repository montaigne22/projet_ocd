from datetime import timedelta
from urllib.parse import quote

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.ocd_live import tools

from .res_company import WEEKDAYS

# What sends a store back to the check of the team when the vendor changes it: where it is and how
# it looks. The opening hours, the phone and « closed until » change at once.
CHECKED_FIELDS = ("kind", "city_id", "district_id", "landmark", "latitude", "longitude", "photo")
# A position measured by the phone with a worse accuracy is not a position of the store
POSITION_MAX_METERS = 200
# The visits of the stores kept for the statistics, a little more than a year
TAPS_KEPT_DAYS = 400


class OcdVendorPlace(models.Model):
    """A place where the customers find a vendor (plan of « My products », chantier 17): a store
    open to the public (address, landmark, position, front, hours: checked by the team before the
    customers see it), or the home of a vendor who sells from home (the customers see the district
    and « By appointment » only; the team sees the address, for the couriers)."""

    _name = "ocd.vendor.place"
    _description = "Place Of A Vendor"
    _inherit = ["mail.thread"]
    _order = "sequence, id"
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        required=True,
        index=True,
        ondelete="cascade",
        domain=[("ocd_is_vendor", "=", True)],
    )
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    kind = fields.Selection(
        selection=[("store", "Store open to the public"), ("home", "Sells from home")],
        required=True,
        default="store",
        tracking=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    city_id = fields.Many2one(comodel_name="res.city", string="City", tracking=True)
    district_id = fields.Many2one(
        comodel_name="res.city.district",
        string="District",
        domain="[('city_id', '=?', city_id)]",
        tracking=True,
    )
    country_id = fields.Many2one(related="city_id.country_id", store=True, string="Country")
    landmark = fields.Char(
        tracking=True,
        help="A well-known place near the store (opposite the pharmacy, behind the market): the "
        "customers and the couriers find it.",
    )
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    position_accuracy = fields.Integer(string="Accuracy (m)", help="How precise the phone was, in meters.")
    photo = fields.Image(string="Front", max_width=1920, max_height=1920, help="The front of the store, its sign seen.")
    phone = fields.Char(help="The phone of the store; the one of the vendor when empty.")
    hour_ids = fields.One2many(
        comodel_name="ocd.vendor.place.hour", inverse_name="place_id", string="Opening Hours", copy=True
    )
    closed_until = fields.Date(string="Closed Until", help="Closed for a while: open again the day after.")
    state = fields.Selection(
        selection=[("to_check", "To check"), ("approved", "Online"), ("refused", "Refused")],
        required=True,
        default="to_check",
        tracking=True,
        index=True,
    )
    review_date = fields.Datetime(string="Checked At", readonly=True, copy=False)
    refuse_reason_id = fields.Many2one(
        comodel_name="ocd.listing.refuse.reason",
        string="Reason Of The Refusal",
        domain=[("applies_to", "=", "store")],
        copy=False,
        tracking=True,
    )
    previous_refusal = fields.Char(string="Sent Again After", readonly=True, copy=False)
    tap_ids = fields.One2many(comodel_name="ocd.vendor.place.tap", inverse_name="place_id", string="Visits")
    form_token = fields.Char(
        copy=False, readonly=True, help="The form that added the place: sent twice, it adds one place only."
    )

    _form_token_uniq = models.Constraint(
        "unique(vendor_id, form_token)", "This place was already added from this form."
    )
    _position_on_earth = models.Constraint(
        "CHECK(latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)",
        "The position must be on Earth.",
    )

    @api.constrains("kind", "vendor_id")
    def _check_home_allowed(self):
        for place in self:
            if place.kind == "home" and not place.company_id.ocd_place_home_allowed:
                raise ValidationError(self.env._("Selling from home is not offered: add a store open to the public."))

    # === WHAT THE CUSTOMERS SEE === #

    def _ocd_has_position(self):
        self.ensure_one()
        return bool(self.latitude or self.longitude)

    def _ocd_area(self):
        """« Akwa, Douala »: the district and the city."""
        self.ensure_one()
        return ", ".join(name for name in (self.district_id.name, self.city_id.name) if name)

    def _ocd_address_line(self):
        """The district and the landmark of a store; the district only for a home."""
        self.ensure_one()
        if self.kind == "home":
            return self._ocd_area()
        return " · ".join(part for part in (self._ocd_area(), self.landmark) if part)

    def _ocd_directions_url(self):
        """The itinerary to the store in the maps chosen in the settings (from where the customer
        is), by its position, else by its address."""
        self.ensure_one()
        maps = self.company_id.ocd_place_maps
        if self._ocd_has_position():
            point = f"{self.latitude:.6f},{self.longitude:.6f}"
            if maps == "osm":
                return f"https://www.openstreetmap.org/directions?to={point}"
            return f"https://www.google.com/maps/dir/?api=1&destination={point}"
        query = quote(", ".join(part for part in (self.landmark, self._ocd_area()) if part))
        if maps == "osm":
            return f"https://www.openstreetmap.org/search?query={query}"
        return f"https://www.google.com/maps/search/?api=1&query={query}"

    def _ocd_phone(self):
        self.ensure_one()
        return self.phone or self.vendor_id.phone or ""

    def _ocd_tz(self):
        self.ensure_one()
        return pytz.timezone(self.vendor_id._ocd_tz_name())

    def _ocd_intervals(self):
        """{weekday (0 Monday): [(from, to)]} of the opening hours."""
        self.ensure_one()
        intervals = {day: [] for day in range(7)}
        for hour in self.hour_ids.sorted(lambda h: (int(h.weekday), h.hour_from)):
            intervals[int(hour.weekday)].append((hour.hour_from, hour.hour_to))
        return intervals

    def _ocd_hours_lines(self):
        """The opening hours as lines grouping the days with the same hours: « Mon.–Sat.: 08:00–19:00 »,
        « Sun.: closed »."""
        self.ensure_one()
        _ = self.env._
        names = [_("Mon."), _("Tue."), _("Wed."), _("Thu."), _("Fri."), _("Sat."), _("Sun.")]
        intervals = self._ocd_intervals()
        texts = [
            ", ".join(f"{tools.hour_text(start)}–{tools.hour_text(end)}" for start, end in intervals[day]) or _("closed")
            for day in range(7)
        ]
        lines, start = [], 0
        for day in range(1, 8):
            if day == 7 or texts[day] != texts[start]:
                days = names[start] if day - 1 == start else f"{names[start]}–{names[day - 1]}"
                lines.append(f"{days}: {texts[start]}")
                start = day
        return lines

    def _ocd_open_state(self, now=None):
        """Whether the store is open now, at its hour (also for a customer abroad): {"open",
        "label"}: « Open · closes at 19:00 », « Closed · opens tomorrow at 08:00 », « Closed until
        2 January »."""
        self.ensure_one()
        _ = self.env._
        tz = self._ocd_tz()
        local = pytz.utc.localize(now or fields.Datetime.now()).astimezone(tz)
        today = local.date()
        if self.closed_until and today <= self.closed_until:
            day = tools.day_text(self.env, self.closed_until, "d MMMM")
            return {"open": False, "label": _("Closed until %s", day)}
        intervals = self._ocd_intervals()
        hour = local.hour + local.minute / 60
        for start, end in intervals[today.weekday()]:
            if start <= hour < end:
                return {"open": True, "label": _("Open · closes at %s", tools.hour_text(end))}
        for offset in range(0, 8):
            day = today + timedelta(days=offset)
            if self.closed_until and day <= self.closed_until:
                continue
            for start, _end in intervals[day.weekday()]:
                if offset == 0 and start <= hour:
                    continue
                at = tools.hour_text(start)
                if offset == 0:
                    return {"open": False, "label": _("Closed · opens at %s", at)}
                if offset == 1:
                    return {"open": False, "label": _("Closed · opens tomorrow at %s", at)}
                return {"open": False, "label": _("Closed · opens %(day)s at %(hour)s",
                                                  day=tools.day_text(self.env, day, "EEEE"), hour=at)}
        return {"open": False, "label": _("Closed")}

    @api.model
    def _ocd_shown_places(self, vendor):
        """The places of `vendor` the customers see: online, in their order, as many as the
        vendor may have (one without OCD Business: the others are kept, not shown)."""
        places = self.sudo().search(
            [("vendor_id", "=", vendor.id), ("state", "=", "approved")], order="sequence, id"
        )
        return places[:vendor._ocd_places_allowed()]

    # === THE VENDOR ADDS AND CHANGES THEIR PLACES === #

    def _ocd_needs_check(self):
        """A store is checked by the team (setting); a home is shown at once: only its district
        is seen by the customers."""
        self.ensure_one()
        return self.kind == "store" and self.company_id.ocd_place_check

    def _ocd_missing_proof(self):
        """What a store still needs to be checked (setting): its front, its position."""
        self.ensure_one()
        if self.kind != "store" or not self.company_id.ocd_place_proof_required:
            return []
        missing = []
        if not self.photo:
            missing.append("photo")
        if not self._ocd_has_position():
            missing.append("position")
        return missing

    @api.model
    def _ocd_vendor_create(self, vendor, values):
        """A place added by the vendor from their space: online at once when it needs no check."""
        if vendor._ocd_places_left() <= 0:
            raise UserError(self.env._("You have all the places you can have. Write to OCD Live for more."))
        place = self.sudo().create({**values, "vendor_id": vendor.id, "state": "to_check"})
        if not place._ocd_needs_check():
            place.write({"state": "approved", "review_date": fields.Datetime.now()})
        place.message_post(body=self.env._("Added by the vendor."))
        return place

    def _ocd_vendor_update(self, values):
        """The changes of the vendor: a new address, position or front send a store back to the
        check of the team (the customers do not see it meanwhile: its old address may be wrong);
        the hours, the phone and « closed until » change at once."""
        self.ensure_one()
        place = self.sudo()
        checked = any(
            field in values and place._fields[field].convert_to_write(place[field], place) != values[field]
            for field in CHECKED_FIELDS
        )
        place.write(values)
        if checked or place.state == "refused":
            if place._ocd_needs_check():
                previous = place.refuse_reason_id.name if place.state == "refused" else False
                place.write({"state": "to_check", "refuse_reason_id": False, "previous_refusal": previous})
                place.message_post(body=self.env._("Changed by the vendor: to check again."))
            else:
                place.write({"state": "approved", "refuse_reason_id": False, "review_date": fields.Datetime.now()})
        return True

    def _ocd_set_hours(self, intervals):
        """Replace the opening hours with `intervals` {weekday: [(from, to)]}."""
        self.ensure_one()
        commands = [fields.Command.clear()] + [
            fields.Command.create({"weekday": str(day), "hour_from": start, "hour_to": end})
            for day, ranges in intervals.items() for start, end in ranges
        ]
        self.sudo().hour_ids = commands

    # === THE CHECK OF THE TEAM === #

    def action_ocd_approve(self):
        for place in self:
            place.write({
                "state": "approved", "review_date": fields.Datetime.now(),
                "refuse_reason_id": False, "previous_refusal": False,
            })
            place.message_post(body=self.env._("Put online."))
        self._ocd_tell_vendor_review()
        return True

    def action_ocd_refuse(self, reason=None):
        """Refuse the places with `reason` (from the form: the reason chosen on it): the vendor
        reads its message in « My stores », corrects and sends it again."""
        for place in self:
            why = reason or place.refuse_reason_id
            if not why:
                raise UserError(self.env._("Choose the reason sent to the vendor."))
            place.write({"state": "refused", "review_date": fields.Datetime.now(), "refuse_reason_id": why.id})
            place.message_post(body=self.env._("Refused: %s", why.name))
        self._ocd_tell_vendor_review()
        return True

    def _ocd_tell_vendor_review(self):
        """Tell the vendors the answer of the team on their stores (shown, or refused with its
        reason): sent on WhatsApp by `ocd_live_shop_whatsapp`."""
        return False

    def _ocd_vendor_places_path(self):
        """« My stores » of the vendor, opened by their personal link (the button of a WhatsApp
        message): without the domain, Meta adds it."""
        self.ensure_one()
        return f"ocd/espace/{self.vendor_id._ocd_get_space_token()}/magasins"

    def _ocd_refusal_text(self):
        self.ensure_one()
        if self.state != "refused":
            return False
        return self.refuse_reason_id.message or self.refuse_reason_id.name or self.env._("Write to OCD Live to know why.")

    def action_ocd_open_map(self):
        self.ensure_one()
        if not self._ocd_has_position():
            raise UserError(self.env._("The vendor did not take the position of this place."))
        return {
            "type": "ir.actions.act_url",
            "url": f"https://www.google.com/maps/search/?api=1&query={self.latitude:.6f},{self.longitude:.6f}",
            "target": "new",
        }

    # === VISITS === #

    def _ocd_week_taps(self):
        """{place id: {kind: count}} of the last 7 days, for the places of `self`, in one query."""
        counts = {place.id: {"itinerary": 0, "call": 0, "whatsapp": 0} for place in self}
        if not self:
            return counts
        since = fields.Datetime.now() - timedelta(days=7)
        groups = self.env["ocd.vendor.place.tap"].sudo()._read_group(
            [("place_id", "in", self.ids), ("create_date", ">=", since)], ["place_id", "kind"], ["__count"]
        )
        for place, kind, count in groups:
            counts[place.id][kind] = count
        return counts


class OcdVendorPlaceHour(models.Model):
    _name = "ocd.vendor.place.hour"
    _description = "Opening Hours Of A Place"
    _order = "weekday, hour_from"

    place_id = fields.Many2one(comodel_name="ocd.vendor.place", required=True, index=True, ondelete="cascade")
    weekday = fields.Selection(selection=WEEKDAYS, string="Day", required=True)
    hour_from = fields.Float(string="From", required=True, default=8.0)
    hour_to = fields.Float(string="To", required=True, default=19.0)

    @api.constrains("hour_from", "hour_to")
    def _check_hours(self):
        for hour in self:
            if not 0 <= hour.hour_from < hour.hour_to <= 24:
                raise ValidationError(self.env._("The store opens before it closes, within the day."))


class OcdVendorPlaceTap(models.Model):
    """A customer who asked for the itinerary of a store, called it or wrote to it: « 18
    itineraries this week » for the vendor."""

    _name = "ocd.vendor.place.tap"
    _description = "Visit Of A Place"
    _order = "id desc"

    place_id = fields.Many2one(comodel_name="ocd.vendor.place", required=True, index=True, ondelete="cascade")
    kind = fields.Selection(
        selection=[("itinerary", "Itinerary"), ("call", "Call"), ("whatsapp", "WhatsApp")], required=True
    )

    @api.autovacuum
    def _gc_old_taps(self):
        limit = fields.Datetime.now() - timedelta(days=TAPS_KEPT_DAYS)
        self.sudo().search([("create_date", "<", limit)]).unlink()
