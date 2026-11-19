from datetime import date, timedelta

from odoo import Command, fields

from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon


class OcdAmbassadorCommon(OcdShopCommon):
    """Grâce Mbia, ambassador in Douala (her link GRACE7), shares the wax dress of Brenda Wax
    (12 000 F, commission of OCD 15 %); Estelle orders with her link."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cameroon = cls.env.ref("base.cm")
        cls.company.write({
            "ocd_ambassador_open": "all", "ocd_ambassador_rate": 5.0, "ocd_ambassador_cap": 3000.0,
            "ocd_ambassador_link_days": 7, "ocd_ambassador_confirm_days": 7, "ocd_ambassador_min_payout": 2000.0,
            "ocd_ambassador_id_above": 50000.0, "ocd_ambassador_pause_rate": 30, "ocd_ambassador_pause_min": 10,
            "ocd_ambassador_customer_month": 5, "ocd_ambassador_momo_hold_hours": 48, "ocd_studio_tz": "Africa/Douala",
        })
        cls.grace = cls.env["res.partner"].create({
            "name": "Grâce Mbia", "phone": "+237 691234567", "country_id": cls.cameroon.id,
            "ocd_ambassador_state": "active", "ocd_ambassador_code": "GRACE7",
            "ocd_ambassador_since": date(2026, 11, 2), "ocd_payout_momo": "+237 677401218",
            "ocd_payout_frequency": "weekly",
        })
        cls.dress.product_tmpl_id.write({"is_published": True, "ocd_review_state": "approved"})
        cls.Gain = cls.env["ocd.ambassador.gain"]

    def _amb_order(self, customer=None, lines=None, ambassador=None, at=None, confirm=True):
        order = self.env["sale.order"].create({
            "partner_id": (customer or self.estelle).id,
            "order_line": [
                Command.create({"product_id": product.id, "product_uom_qty": qty, "tax_ids": [Command.clear()]})
                for product, qty in (lines or [(self.dress, 1)])
            ],
        })
        order.write({"ocd_ambassador_id": (ambassador or self.grace).id,
                     "ocd_ambassador_at": at or fields.Datetime.now() - timedelta(hours=2)})
        if confirm:
            order.action_confirm()
        return order

    def _deliver(self, parcel):
        parcel.action_ocd_ready()
        parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()
        parcel._ocd_collect("online", self.courier, reference="CP-1")
        delivered, _left = parcel._ocd_check_code(parcel.sudo().ocd_delivery_code)
        self.assertTrue(delivered)

    def _gain(self, order):
        return self.Gain.search([("order_id", "=", order.id)])

    def _confirm_due(self, gains):
        gains.write({"confirm_on": self.company._ocd_local_today()})
        self.Gain._cron_ocd_ambassadors()
