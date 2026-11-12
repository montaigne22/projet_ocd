from odoo import fields, models


class OcdLiveDemoEvent(models.Model):
    """A step of the scenario of the demo that took place (an order, a parcel that left, a
    WhatsApp message): each step happens once, even when the scheduled action of the demo runs
    late, twice, or after a stop of the server."""

    _name = "ocd.live.demo.event"
    _description = "Step Of The OCD Live Demo"
    _order = "id"

    key = fields.Char(required=True, index=True)
    sale_order_id = fields.Many2one(comodel_name="sale.order", ondelete="cascade", index="btree_not_null")

    _unique_key = models.Constraint("UNIQUE (key)", "A step of the demo takes place once.")
