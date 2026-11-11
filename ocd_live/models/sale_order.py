from datetime import timedelta

from odoo import Command, api, fields, models
from odoo.tools import format_date

from .ocd_live_price_rule import percent_text


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ocd_booking_ids = fields.One2many(
        comodel_name="ocd.live.booking", inverse_name="sale_order_id", string="Lives"
    )
    ocd_booking_count = fields.Integer(string="Lives Count", compute="_compute_ocd_booking_count")
    ocd_pass_ids = fields.One2many(
        comodel_name="ocd.directory.pass", inverse_name="sale_order_id", string="Directory Passes"
    )
    ocd_payment_declared_date = fields.Datetime(
        string="Payment Announced On",
        copy=False,
        help="The vendor says the payment checked by the team was sent (Mobile Money to the "
        "number of OCD): the hour of the live stays held while the team checks it.",
    )
    ocd_payment_reference = fields.Char(
        string="Announced Payment",
        copy=False,
        help="Number that paid or reference of the transfer, given by the vendor.",
    )
    ocd_payment_help_date = fields.Datetime(
        string="Payment Help Asked On",
        copy=False,
        help="No payment method of the website takes the payments of the country of the vendor: "
        "the vendor asked the team for help. The hour of the live stays held meanwhile.",
    )

    def _ocd_announce_payment(self, reference):
        """The vendor says the payment checked by the team was sent: the hours of its lives stay
        held while the team checks it (« Slot Held For A Payment Checked By The Team »), and the
        team is told in the order and in the channel of the lives."""
        self.ensure_one()
        now = fields.Datetime.now()
        self.write({"ocd_payment_declared_date": now, "ocd_payment_reference": reference or False})
        hold = now + timedelta(hours=self.company_id.ocd_manual_hold_hours)
        for booking in self.ocd_booking_ids.filtered(lambda b: b.state == "draft"):
            booking.hold_until = max(booking.hold_until or now, hold)
        body = self.env._(
            "%(vendor)s says the payment of %(order)s was sent (%(reference)s): check it, then confirm it.",
            vendor=self.partner_id.name,
            order=self.name,
            reference=reference or self.env._("no number nor reference given"),
        )
        self.message_post(body=body, message_type="comment", subtype_xmlid="mail.mt_note")
        channel = self.company_id.ocd_lives_channel_id
        if channel:
            channel.sudo().message_post(body=body, message_type="comment", subtype_xmlid="mail.mt_comment")

    def _ocd_ask_payment_help(self):
        """No payment method takes the payments of the country of the vendor (a country opened
        before its payment): the vendor asks the team. The hours of its lives stay held while
        the team answers (« Slot Held For A Payment Checked By The Team »); the team is told in
        the order, in the channel of the lives, and by an activity for the person in charge."""
        self.ensure_one()
        if self.ocd_payment_help_date:
            return False
        now = fields.Datetime.now()
        self.ocd_payment_help_date = now
        hold = now + timedelta(hours=self.company_id.ocd_manual_hold_hours)
        for booking in self.ocd_booking_ids.filtered(lambda b: b.state == "draft"):
            booking.hold_until = max(booking.hold_until or now, hold)
        body = self.env._(
            "%(vendor)s (%(country)s, %(phone)s) cannot pay %(order)s online: no payment method takes "
            "the payments of the country. Write to them on WhatsApp to agree on the payment.",
            vendor=self.partner_id.name,
            country=self.partner_id.country_id.name or "-",
            phone=self.partner_id.phone or "-",
            order=self.name,
        )
        self.message_post(body=body, message_type="comment", subtype_xmlid="mail.mt_note")
        channel = self.company_id.ocd_lives_channel_id
        if channel:
            channel.sudo().message_post(body=body, message_type="comment", subtype_xmlid="mail.mt_comment")
        responsible = (
            self.company_id.ocd_live_responsible_id
            or self.user_id
            or self.env.ref("ocd_live.group_ocd_live_manager").sudo().all_user_ids.filtered(lambda user: user.active and not user.share)[:1]
        )
        if responsible:
            self.sudo().activity_schedule(
                "mail.mail_activity_data_todo",
                summary=self.env._("Payment to agree on WhatsApp"),
                note=body,
                user_id=responsible.id,
            )
        return True

    @api.depends("ocd_booking_ids")
    def _compute_ocd_booking_count(self):
        for order in self:
            order.ocd_booking_count = len(order.ocd_booking_ids)

    def _action_confirm(self):
        """Override of `sale` to turn the paid packages into credits and confirmed lives, and
        the paid passes into directory passes. The payment provider confirms the order: the
        lives are never confirmed by the browser."""
        result = super()._action_confirm()
        self.order_line._ocd_process_confirmed_lines()
        return result

    def _action_cancel(self):
        result = super()._action_cancel()
        self.ocd_booking_ids.filtered(lambda b: b.state == "draft").action_cancel()
        return result

    def action_ocd_view_bookings(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("ocd_live.ocd_live_booking_action")
        action["domain"] = [("sale_order_id", "=", self.id)]
        return action

    def _ocd_add_hour_price_line(self, start, mode, percent, per_live):
        """Add the price change of the hour of a live: `percent` of the price of one live."""
        self.ensure_one()
        local = self.partner_id._ocd_to_local(start)  # read by the vendor: their hour
        product = self.env.ref("ocd_live.product_hour_price").sudo().product_variant_id
        self.sudo().write({"order_line": [Command.create({
            "product_id": product.id,
            "name": self.env._(
                "Price of the hour: %(day)s at %(hour)s (%(percent)s)",
                day=format_date(self.env, local.date()),
                hour=local.strftime("%H:%M"),
                percent=percent_text(percent),
            ),
            "product_uom_qty": 1,
            "price_unit": self.currency_id.round(per_live * percent / 100),
        })]})
        return self.order_line[-1:]

    # === PAYMENT PAGE OF OCD LIVE === #

    def _ocd_payment_state(self):
        """Return the step of the payment page: form, waiting, failed, done or cancelled. The
        page shows the payment form of Odoo: the providers and their methods depend on the
        country, the currency and the amount of the order, as configured by the team."""
        self.ensure_one()
        if self.state == "sale":
            return "done"
        if self.state == "cancel":
            return "cancelled"
        last = self.transaction_ids.sorted("id")[-1:]
        if last.state in ("pending", "authorized", "done"):
            # Paid or being paid: the processing of the payment confirms the order
            return "waiting"
        if last.state in ("error", "cancel"):
            return "failed"
        return "form"
