from odoo import fields, models


class OcdLiveBookingSlot(models.Model):
    """One reserved slot of the shared calendar.

    A booking reserves one row per slot it takes (three for a 4-hour live). The unique index
    on the start of the slot makes a double booking impossible, even when two vendors pay at
    the same second: only one transaction can insert the row.
    """

    _name = "ocd.live.booking.slot"
    _description = "Reserved Live Slot"
    _order = "start_datetime, id"

    booking_id = fields.Many2one(
        comodel_name="ocd.live.booking", required=True, index=True, ondelete="cascade"
    )
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, ondelete="cascade"
    )
    start_datetime = fields.Datetime(string="Start", required=True)

    _unique_company_start = models.UniqueIndex(
        "(company_id, start_datetime)",
        "This time slot is already taken.",
    )
