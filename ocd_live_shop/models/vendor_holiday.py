"""The holiday mode of a vendor (chantier 20, A.5 of the plan of « My products », design
VacancesProximite).

« Back on 2 January » on the boutique: the products stay visible, the orders are paused (the
cart, the payment and the WhatsApp of a vendor in direct contact), and the customers ask to be
told when the vendor is back. On the day of the return, at the hour of the vendor (or when they
come back sooner), the holiday ends and the customers who asked are told on WhatsApp. The lives
already booked do not move."""
from datetime import timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.ocd_live import tools


class ResPartner(models.Model):
    _inherit = "res.partner"

    ocd_holiday_until = fields.Date(
        string="On Holiday Until",
        copy=False,
        tracking=True,
        help="The vendor is on holiday until this day, when the orders start again: the products stay "
        "visible, the orders are paused, the customers can ask to be told of the return.",
    )
    ocd_holiday_note = fields.Char(
        string="Word Of The Holiday",
        copy=False,
        help="Shown on the boutique while the vendor is on holiday.",
    )

    def _ocd_today(self):
        """The day of today at the hour of the vendor."""
        self.ensure_one()
        tz = pytz.timezone(self._ocd_tz_name())
        return pytz.utc.localize(fields.Datetime.now()).astimezone(tz).date()

    def _ocd_on_holiday(self):
        """Whether the orders of the vendor are paused: on holiday until a day still to come."""
        self.ensure_one()
        vendor = self.sudo()
        return bool(vendor.ocd_holiday_until) and vendor._ocd_today() < vendor.ocd_holiday_until

    def _ocd_holiday_back_text(self):
        """« Friday 2 January »: the day of the return, in the language of the page."""
        self.ensure_one()
        return tools.day_text(self.env, self.sudo().ocd_holiday_until, "EEEE d MMMM")

    def _ocd_holiday_max_days(self):
        self.ensure_one()
        return max((self.company_id or self.env.company).ocd_holiday_max_days or 60, 1)

    def _ocd_start_holiday(self, until, note=False):
        """The vendor leaves on holiday until `until` (the day the orders start again): at least
        tomorrow, at most the days of the setting (60 by default)."""
        self.ensure_one()
        vendor = self.sudo()
        if not vendor.ocd_is_vendor:
            raise UserError(self.env._("Only a vendor can go on holiday."))
        today = vendor._ocd_today()
        until = fields.Date.to_date(until)
        if not until or until <= today:
            raise UserError(self.env._("Choose the day you are back: tomorrow at the earliest."))
        longest = vendor._ocd_holiday_max_days()
        if until > today + timedelta(days=longest):
            raise UserError(self.env._("%s days at most: choose an earlier day.", longest))
        vendor.write({"ocd_holiday_until": until, "ocd_holiday_note": (note or "").strip()[:160] or False})
        vendor.message_post(body=self.env._("On holiday until %s.", fields.Date.to_string(until)))
        return True

    def _ocd_end_holiday(self):
        """The holiday ends (the day of the return, or the vendor comes back sooner): the orders
        start again and the customers who asked are told."""
        vendors = self.sudo().filtered("ocd_holiday_until")
        if not vendors:
            return False
        vendors.write({"ocd_holiday_until": False, "ocd_holiday_note": False})
        for vendor in vendors:
            vendor.message_post(body=self.env._("Back from holiday: the orders start again."))
        self.env["ocd.boutique.alert"].sudo()._ocd_send_vendors_back(vendors)
        return True

    @api.model
    def _cron_holiday_back(self):
        """The vendors whose day of return came, at their hour."""
        vendors = self.sudo().search([("ocd_holiday_until", "!=", False)])
        vendors.filtered(lambda vendor: not vendor._ocd_on_holiday())._ocd_end_holiday()

    def _ocd_holiday_waiting_count(self):
        """The customers who asked to be told of the return."""
        self.ensure_one()
        return self.env["ocd.boutique.alert"].sudo().search_count([
            ("vendor_id", "=", self.id), ("kind", "=", "back"), ("state", "=", "waiting"),
        ])


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _ocd_holiday_vendors(self):
        """The vendors of the products of the cart who are on holiday."""
        self.ensure_one()
        vendors = self.order_line.filtered(lambda line: not line.is_delivery).product_id.sudo().product_tmpl_id.ocd_vendor_id
        return vendors.filtered(lambda vendor: vendor._ocd_on_holiday())

    def _ocd_holiday_message(self):
        """What the cart says when a vendor of its products is on holiday, or False."""
        self.ensure_one()
        vendors = self._ocd_holiday_vendors()
        if not vendors:
            return False
        vendor = vendors[0]
        return self.env._(
            "%(vendor)s is on holiday until %(day)s: remove their products from the cart, or order them on their return.",
            vendor=vendor.name, day=vendor._ocd_holiday_back_text(),
        )

    def _is_cart_ready_for_checkout(self):
        """Override of `website_sale`: the orders of a vendor on holiday are paused (also the
        payment of a cart filled before the holiday)."""
        message = self._ocd_holiday_message()
        if message:
            self._add_blocking_alert(message)
            return False
        return super()._is_cart_ready_for_checkout()
