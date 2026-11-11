from odoo import api, fields, models
from odoo.fields import Domain


class StockMove(models.Model):
    _inherit = "stock.move"

    ocd_vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="OCD Vendor",
        compute="_compute_ocd_vendor_id",
        store=True,
        index="btree_not_null",
    )

    @api.depends("sale_line_id.ocd_vendor_id")
    def _compute_ocd_vendor_id(self):
        for move in self:
            move.ocd_vendor_id = move.sale_line_id.ocd_vendor_id

    def _key_assign_picking(self):
        """Override of `stock` to give each vendor its own parcel."""
        return super()._key_assign_picking() + (self.ocd_vendor_id,)

    def _search_picking_for_assignation_domain(self):
        """Override of `stock` so that a move only joins a parcel of the same vendor."""
        return Domain.AND([
            super()._search_picking_for_assignation_domain(),
            [("ocd_vendor_id", "=", self.ocd_vendor_id.id)],
        ])

    def _get_new_picking_values(self):
        values = super()._get_new_picking_values()
        values["ocd_vendor_id"] = self.ocd_vendor_id[:1].id
        return values

    def _assign_picking_post_process(self, new=False):
        """Override of `stock` to turn the new deliveries of shop orders into parcels."""
        super()._assign_picking_post_process(new=new)
        pickings = self.picking_id
        for picking in pickings.filtered("ocd_is_parcel"):
            picking.ocd_goods_amount = picking._ocd_compute_goods_amount()
        pickings.filtered(lambda p: not p.ocd_is_parcel)._ocd_init_parcels()

    def _action_done(self, cancel_backorder=False):
        """A product received again: the customers who asked are told at once (the scheduled
        task checks again every 30 minutes)."""
        done = super()._action_done(cancel_backorder=cancel_backorder)
        products = done.filtered(lambda move: move.location_dest_id.usage == "internal").product_id
        if products and self.env["ocd.stock.alert"].sudo().search_count(
            [("state", "=", "waiting"), ("product_id", "in", products.ids)], limit=1
        ):
            self.env.ref("ocd_live_shop.ir_cron_stock_alerts").sudo()._trigger()
        return done
