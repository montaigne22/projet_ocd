from datetime import timedelta

from odoo import api, fields, models

from .res_company import DELIVERY_MODES, PAYOUT_FREQUENCIES


class ResPartner(models.Model):
    _inherit = "res.partner"

    # === VENDOR: SALE AND DELIVERY === #

    ocd_sale_mode = fields.Selection(
        selection=[("direct", "Direct contact on WhatsApp"), ("ocd", "Sold by OCD")],
        string="How The Customers Buy",
        default="direct",
        tracking=True,
        help="Direct contact: the customers write to the vendor on WhatsApp. Sold by OCD: "
        "the customers pay OCD in the shop and OCD pays the vendor back.",
    )
    ocd_delivery_mode = fields.Selection(
        selection=DELIVERY_MODES,
        string="Who Delivers",
        default=lambda self: self.env.company.ocd_default_delivery_mode,
        tracking=True,
    )
    ocd_zone_ids = fields.Many2many(
        comodel_name="res.city.district",
        relation="res_partner_ocd_zone_rel",
        column1="partner_id",
        column2="district_id",
        string="Delivery Zones",
        help="Districts where the vendor delivers. Elsewhere, an OCD courier delivers when "
        "the fallback is enabled.",
    )
    ocd_zone_fallback = fields.Boolean(
        string="OCD Courier Outside The Zones",
        default=True,
    )
    ocd_vendor_collects = fields.Boolean(
        string="Collects The Payment At The Door",
        help="The vendor may collect the money of the orders paid at the door. The "
        "commission of OCD is then withheld from the next payout.",
    )
    ocd_prep_hours = fields.Integer(
        string="Hours To Prepare A Parcel",
        help="0: the time of the settings.",
    )
    ocd_commission_rate = fields.Float(
        string="Commission (%)",
        default=lambda self: self.env.company.ocd_default_commission,
        tracking=True,
    )
    ocd_payout_frequency = fields.Selection(
        selection=PAYOUT_FREQUENCIES,
        string="Payout Rhythm",
        default=lambda self: self.env.company.ocd_default_payout_frequency,
        tracking=True,
    )
    ocd_payout_momo = fields.Char(string="Mobile Money For The Payouts")
    ocd_late_count = fields.Integer(
        string="Late Parcels (30 Days)", compute="_compute_ocd_late_count"
    )

    # === COURIER === #

    ocd_is_courier = fields.Boolean(string="OCD Courier", index=True)
    ocd_courier_kind = fields.Selection(
        selection=[("employee", "Employee of OCD"), ("company", "Delivery company")],
        string="Courier Type",
        default="employee",
    )
    ocd_courier_zone_ids = fields.Many2many(
        comodel_name="res.city.district",
        relation="res_partner_ocd_courier_zone_rel",
        column1="partner_id",
        column2="district_id",
        string="Courier Zones",
    )
    ocd_courier_available = fields.Boolean(string="On Duty", default=True)
    ocd_cash_on_hand = fields.Monetary(
        string="Cash To Hand Over",
        compute="_compute_ocd_cash_on_hand",
        currency_field="currency_id",
    )
    def _compute_ocd_late_count(self):
        since = fields.Datetime.now() - timedelta(days=30)
        counts = {
            vendor.id: count
            for vendor, count in self.env["stock.picking"]._read_group(
                [
                    ("ocd_vendor_id", "in", self.ids),
                    ("ocd_escalated_at", ">=", since),
                ],
                ["ocd_vendor_id"],
                ["__count"],
            )
        }
        for partner in self:
            partner.ocd_late_count = counts.get(partner.id, 0)

    def _compute_ocd_cash_on_hand(self):
        totals = {
            courier.id: amount
            for courier, amount in self.env["stock.picking"]._read_group(
                [
                    ("ocd_cod_collected_by_id", "in", self.ids),
                    ("ocd_cod_state", "=", "collected"),
                    ("ocd_cod_method", "=", "cash"),
                ],
                ["ocd_cod_collected_by_id"],
                ["ocd_cod_collected_amount:sum"],
            )
        }
        for partner in self:
            partner.ocd_cash_on_hand = totals.get(partner.id, 0.0)

    @api.model
    def _ocd_find_courier(self, district, company=None):
        """Return an OCD courier on duty who covers `district`, the least busy first."""
        if not district:
            return self.browse()
        couriers = self.search([
            ("ocd_is_courier", "=", True),
            ("ocd_courier_available", "=", True),
            ("ocd_courier_zone_ids", "in", district.ids),
        ])
        if not couriers:
            return self.browse()
        loads = {
            courier.id: count
            for courier, count in self.env["stock.picking"]._read_group(
                [
                    ("ocd_courier_id", "in", couriers.ids),
                    ("ocd_stage", "in", ("to_prepare", "ready", "picked", "on_the_way")),
                ],
                ["ocd_courier_id"],
                ["__count"],
            )
        }
        return couriers.sorted(lambda c: (loads.get(c.id, 0), c.id))[:1]

    def _ocd_prep_hours(self):
        self.ensure_one()
        return self.ocd_prep_hours or (self.company_id or self.env.company).ocd_prep_hours

    def _ocd_get_livrer_url(self):
        """Personal link of the delivery app of the vendor or of the courier."""
        self.ensure_one()
        return f"{self.get_base_url()}/ocd/livrer/{self._ocd_get_space_token()}"
