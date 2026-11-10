from odoo import Command
from odoo.tests import TransactionCase


class OcdShopCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True, mail_notrack=True))
        cls.company = cls.env.company
        if not cls.env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", cls.company.id)], limit=1):
            cls.env["account.chart.template"].try_loading("generic_coa", company=cls.company, install_demo=False)
        cls.company.write({
            "ocd_booking_open_date": False,
            "ocd_default_commission": 15.0,
            "ocd_prep_hours": 4,
            "ocd_escalation_hours": 2,
            "ocd_code_max_attempts": 3,
            "ocd_max_failed_attempts": 2,
            "ocd_cod_cash": True,
            "ocd_cod_online": True,
            "ocd_cod_momo_declared": True,
            "ocd_default_payout_frequency": "weekly",
            "ocd_payout_weekday": "0",
            "ocd_payout_min_amount": 1000,
            "ocd_live_responsible_id": cls.env.ref("base.user_admin").id,
        })
        cls.akwa = cls.env.ref("delivery_cameroon.district_douala_akwa")
        cls.bonaberi = cls.env.ref("delivery_cameroon.district_douala_bonaberi")
        cls.makepe = cls.env.ref("delivery_cameroon.district_douala_makepe")
        douala = cls.akwa.city_id
        cls.courier = cls.env["res.partner"].create({
            "name": "Junior Ekwalla",
            "ocd_is_courier": True,
            "ocd_courier_zone_ids": [Command.set((cls.akwa | cls.makepe).ids)],
        })
        cls.courier_west = cls.env["res.partner"].create({
            "name": "Raoul Nyobe",
            "ocd_is_courier": True,
            "ocd_courier_zone_ids": [Command.set(cls.bonaberi.ids)],
        })
        cls.brenda = cls.env["res.partner"].create({
            "name": "Brenda Wax",
            "ocd_is_vendor": True,
            "ocd_vendor_state": "approved",
            "ocd_sale_mode": "ocd",
            "ocd_delivery_mode": "pickup",
            "ocd_commission_rate": 15.0,
        })
        cls.fatou = cls.env["res.partner"].create({
            "name": "Fatou Karite",
            "ocd_is_vendor": True,
            "ocd_vendor_state": "approved",
            "ocd_sale_mode": "ocd",
            "ocd_delivery_mode": "vendor",
            "ocd_zone_ids": [Command.set((cls.akwa | cls.makepe).ids)],
            "ocd_zone_fallback": True,
            "ocd_commission_rate": 15.0,
        })
        cls.dress = cls._product("Robe en wax", 12000, cls.brenda)
        cls.butter = cls._product("Beurre de karite", 2500, cls.fatou)
        cls.estelle = cls.env["res.partner"].create({
            "name": "Estelle Ngono",
            "phone": "+237 670000000",
            "country_id": cls.env.ref("base.cm").id,
            "city_id": douala.id,
            "district_id": cls.akwa.id,
            "delivery_landmark": "En face de la pharmacie",
        })
        cls.herve = cls.env["res.partner"].create({
            "name": "Herve Kuete",
            "phone": "+237 694000050",
            "country_id": cls.env.ref("base.cm").id,
            "city_id": douala.id,
            "district_id": cls.bonaberi.id,
            "delivery_landmark": "Apres le pont",
        })

    @classmethod
    def _product(cls, name, price, vendor):
        return cls.env["product.product"].create({
            "name": name,
            "type": "consu",
            "list_price": price,
            "taxes_id": [Command.clear()],
            "ocd_vendor_id": vendor.id,
        })

    @classmethod
    def _order(cls, customer, lines):
        order = cls.env["sale.order"].create({
            "partner_id": customer.id,
            "order_line": [
                Command.create({"product_id": product.id, "product_uom_qty": qty, "tax_ids": [Command.clear()]})
                for product, qty in lines
            ],
        })
        order.action_confirm()
        return order

    def _parcel(self, order, vendor):
        return order.picking_ids.filtered(lambda p: p.ocd_vendor_id == vendor)
