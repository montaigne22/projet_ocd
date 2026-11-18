from odoo import api, fields, models
from odoo.exceptions import UserError


class OcdEveningParticipation(models.Model):
    """A vendor who joins a big event: their live during the event (a usual booking) and their
    promos of the evening, checked by the team. The promos show once the participation is
    accepted, and only during the hours of the event."""

    _name = "ocd.evening.participation"
    _description = "Participation In A Big Event"
    _inherit = ["mail.thread"]
    _order = "evening_id desc, id"

    evening_id = fields.Many2one(comodel_name="ocd.evening", string="Big Event", required=True, index=True,
                                 ondelete="cascade")
    vendor_id = fields.Many2one(comodel_name="res.partner", string="Vendor", required=True, index=True,
                                ondelete="cascade")
    company_id = fields.Many2one(related="evening_id.company_id", store=True)
    state = fields.Selection(
        selection=[("to_check", "To check"), ("approved", "Accepted"), ("refused", "Refused")],
        required=True, default="to_check", tracking=True, index=True,
    )
    refuse_reason = fields.Char(string="Why It Was Refused", readonly=True)
    booking_id = fields.Many2one(comodel_name="ocd.live.booking", string="Live During The Event",
                                 compute="_compute_booking_id")
    promo_ids = fields.One2many(comodel_name="ocd.product.promo", inverse_name="participation_id", string="Promos Of The Vendor",
                                context={"active_test": False})
    promo_count = fields.Integer(string="Promos", compute="_compute_promo_count")

    _unique_participation = models.UniqueIndex("(evening_id, vendor_id)", "This vendor already joins this event.")

    def _compute_booking_id(self):
        Booking = self.env["ocd.live.booking"].sudo()
        for participation in self:
            evening = participation.evening_id
            participation.booking_id = Booking.search([
                ("partner_id", "=", participation.vendor_id.id), ("state", "=", "confirmed"),
                ("start_datetime", "<", evening.date_end), ("end_datetime", ">", evening.date_start),
            ], order="start_datetime", limit=1) if evening and participation.vendor_id else Booking

    def _compute_promo_count(self):
        for participation in self:
            participation.promo_count = len(participation.promo_ids.filtered(lambda promo: not promo.stopped_at))

    @api.depends("evening_id", "vendor_id")
    def _compute_display_name(self):
        for participation in self:
            participation.display_name = f"{participation.vendor_id.name} · {participation.evening_id.name}"

    # === THE VENDOR JOINS === #

    @api.model
    def _ocd_submit(self, evening, vendor, prices):
        """`vendor` joins `evening` with `prices` {product template: promo price of the event}
        (none: a live without promos). Sent to the team; the promos show once accepted. Return
        the participation."""
        evening, vendor = evening.sudo(), vendor.sudo()
        env = self.env
        if not evening._ocd_registration_open():
            raise UserError(env._("The registrations of %s are closed.", evening.name))
        if not evening._ocd_invites(vendor):
            raise UserError(env._("This event is for the vendors of %s.", evening._ocd_countries_text()))
        participation = self.sudo().search([("evening_id", "=", evening.id), ("vendor_id", "=", vendor.id)], limit=1)
        if not participation:
            participation = self.sudo().create({"evening_id": evening.id, "vendor_id": vendor.id})
        Promo = env["ocd.product.promo"].sudo()
        limits = {**Promo._ocd_limits(evening.company_id), "discount": evening.max_discount}
        kept = Promo.browse()
        for product, price in prices.items():
            if product.ocd_vendor_id != vendor:
                raise UserError(env._("This product is not yours."))
            try:
                kept |= Promo._ocd_put(
                    product, price, evening.date_end, source="evening", date_start=evening.date_start,
                    limits=limits, evening_id=evening.id, participation_id=participation.id, active=False,
                )
            except UserError as exc:
                raise UserError(f"{product.name}: {exc.args[0]}") from exc
        # The promos taken off the participation
        (participation.promo_ids.filtered(lambda promo: not promo.stopped_at) - kept)._ocd_stop(
            env._("Taken off by the vendor."))
        participation.write({"state": "to_check", "refuse_reason": False})
        participation.message_post(body=env._("Sent by the vendor: %s promos.", len(kept)))
        return participation

    def action_ocd_approve(self):
        """« Accept »: the promos of the event show during its hours."""
        for participation in self:
            participation.state = "approved"
            participation.promo_ids.filtered(lambda promo: not promo.stopped_at).write({"active": True})
            participation.message_post(body=self.env._("Accepted by %s.", self.env.user.name))
        return True

    def action_ocd_refuse(self, reason=None):
        for participation in self:
            participation.write({"state": "refused", "refuse_reason": reason.message or reason.name if reason else False})
            participation.promo_ids.filtered("active").write({"active": False})
            participation.message_post(body=self.env._("Refused: %s", participation.refuse_reason or "-"))
        return True

    def _ocd_state_line(self):
        """What the vendor reads of their participation."""
        self.ensure_one()
        env = self.env
        if self.state == "approved":
            return env._("Accepted: you are in the programme of the event.")
        if self.state == "refused":
            return env._("Refused: %s", self.refuse_reason or "-")
        return env._("Sent: the team checks your participation and writes to you on WhatsApp.")

    @api.model
    def _ocd_invitations(self, vendor):
        """The big events of the space of `vendor`: the ones that invite them, registrations open
        (or joined), with what the card says."""
        if not vendor:
            return []
        env = self.env
        rows = []
        for evening in env["ocd.evening"]._ocd_shown():
            if not evening._ocd_invites(vendor):
                continue
            participation = self.sudo().search([("evening_id", "=", evening.id), ("vendor_id", "=", vendor.id)], limit=1)
            if not participation and not evening._ocd_registration_open():
                continue
            tz_name = vendor._ocd_tz_name()
            rows.append({
                "evening": evening,
                "kicker": env._("%(kind)s · %(when)s", kind=evening._ocd_kind_text(),
                                when=evening._ocd_when_text(tz_name, "EEE d MMM")),
                "title": env._("%s: join", evening.name) if not participation else evening.name,
                "line": participation._ocd_state_line() if participation else env._(
                    "A live during the event and your promos of the event. Registrations until %s.",
                    evening._ocd_registration_day(tz_name)),
                "button": env._("My participation") if participation else env._("Join"),
            })
        return rows
