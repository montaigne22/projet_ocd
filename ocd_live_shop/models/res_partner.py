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
    ocd_delivery_rate_ids = fields.One2many(
        comodel_name="ocd.delivery.rate",
        inverse_name="vendor_id",
        string="Delivery Prices",
        help="Prices of the deliveries made by the vendor, by zone. Elsewhere in their zones, the "
        "vendor delivers at the price of the OCD courier of the city.",
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
    ocd_delivered_30 = fields.Integer(string="Parcels Delivered (30 Days)", compute="_compute_ocd_quality")
    ocd_on_time_rate = fields.Char(string="On Time", compute="_compute_ocd_quality")
    ocd_failed_30 = fields.Integer(string="Failed Deliveries (30 Days)", compute="_compute_ocd_quality")
    ocd_product_count = fields.Integer(string="Products", compute="_compute_ocd_product_count")

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

    def _compute_ocd_quality(self):
        since = fields.Datetime.now() - timedelta(days=30)
        Picking = self.env["stock.picking"]
        for partner in self:
            if not partner.ocd_is_vendor or not partner.id:
                partner.ocd_delivered_30 = partner.ocd_failed_30 = 0
                partner.ocd_on_time_rate = ""
                continue
            delivered = Picking.search([
                ("ocd_vendor_id", "=", partner.id),
                ("ocd_stage", "=", "delivered"),
                ("ocd_delivered_at", ">=", since),
            ])
            partner.ocd_delivered_30 = len(delivered)
            on_time = len(delivered.filtered(lambda parcel: not parcel.ocd_escalated_at))
            partner.ocd_on_time_rate = f"{round(on_time / len(delivered) * 100)} %" if delivered else "—"
            partner.ocd_failed_30 = Picking.search_count([
                ("ocd_vendor_id", "=", partner.id),
                ("ocd_failed_attempts", ">", 0),
                ("create_date", ">=", since),
            ])

    def _compute_ocd_product_count(self):
        counts = {
            vendor.id: count
            for vendor, count in self.env["product.template"]._read_group(
                [("ocd_vendor_id", "in", self.ids)], ["ocd_vendor_id"], ["__count"]
            )
        }
        for partner in self:
            partner.ocd_product_count = counts.get(partner.id, 0)

    @api.model
    def ocd_choice_descriptions(self, field_name):
        descriptions = super().ocd_choice_descriptions(field_name)
        if field_name == "ocd_sale_mode":
            descriptions.update({
                "direct": self.env._(
                    "The customer writes to the vendor. The vendor collects the money and delivers. "
                    "OCD does not touch the money."
                ),
                "ocd": self.env._(
                    "The customer pays on the website or at the door. OCD pays the vendor back, "
                    "minus the commission."
                ),
            })
        elif field_name == "ocd_delivery_mode":
            descriptions.update({
                "vendor": self.env._(
                    "The vendor sees the parcels in the space, delivers, then types the code of the customer."
                ),
                "pickup": self.env._(
                    "The vendor prepares. An OCD courier picks the parcel up, delivers and types the code."
                ),
                "stock": self.env._(
                    "Consignment: the vendor leaves the products at OCD, which delivers from its stock."
                ),
            })
        return descriptions

    def action_ocd_view_products(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("ocd_live_shop.product_template_action_ocd_vendor_products")
        action["domain"] = [("ocd_vendor_id", "=", self.id)]
        action["context"] = {"default_ocd_vendor_id": self.id}
        return action

    def action_ocd_open_boutique(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": f"/ocd/boutique/{self.id}", "target": "new"}

    def action_ocd_deliveries_to_ocd(self):
        """Give the deliveries of a vendor often late to the OCD couriers."""
        self.write({"ocd_delivery_mode": "pickup"})
        for vendor in self:
            vendor.message_post(body=self.env._("Who delivers: an OCD courier picks the parcels up, from now on."))
        return True

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

    def _ocd_checkout_without_email(self, **kwargs):
        """Whether the address of a website order is complete without an e-mail: the customers
        of OCD Live give their WhatsApp number and follow their order on WhatsApp."""
        if self.env.context.get("ocd_whatsapp_checkout"):
            return True
        return bool(kwargs.get("order_sudo")) and len(self) == 1 and bool(self.phone)

    def _get_mandatory_billing_address_fields(self, country_sudo, **kwargs):
        """Override of `portal`: no e-mail needed for the WhatsApp checkout of OCD Live."""
        field_names = super()._get_mandatory_billing_address_fields(country_sudo, **kwargs)
        if self._ocd_checkout_without_email(**kwargs):
            field_names.discard("email")
        return field_names

    def _get_mandatory_delivery_address_fields(self, country_sudo, **kwargs):
        """Override of `portal`: no e-mail needed for the WhatsApp checkout of OCD Live."""
        field_names = super()._get_mandatory_delivery_address_fields(country_sudo, **kwargs)
        if self._ocd_checkout_without_email(**kwargs):
            field_names.discard("email")
        return field_names

    def _ocd_prep_hours(self):
        self.ensure_one()
        return self.ocd_prep_hours or (self.company_id or self.env.company).ocd_prep_hours

    def _ocd_get_livrer_url(self):
        """Personal link of the delivery app of the vendor or of the courier."""
        self.ensure_one()
        return f"{self.get_base_url()}/ocd/livrer/{self._ocd_get_space_token()}"

    def _ocd_send_delivery_link(self, url):
        """Send the link of the delivery app. Extended by ocd_live_shop_whatsapp."""
        return False

    def action_ocd_delivery_app_link(self):
        """Give the vendor or the courier the link of the delivery app."""
        self.ensure_one()
        url = self._ocd_get_livrer_url()
        if self._ocd_send_delivery_link(url):
            message = self.env._("The link of the delivery app was sent on WhatsApp.")
        else:
            message = self.env._("Send this link of the delivery app: %s", url)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": message, "type": "success", "sticky": True},
        }
