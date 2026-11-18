from datetime import datetime

from odoo import Command

from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon


class OcdExpressCommon(OcdShopCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.douala = cls.akwa.city_id
        cls.bonamoussadi = cls.env["res.city.district"].search(
            [("city_id", "=", cls.douala.id), ("id", "not in", (cls.akwa | cls.makepe | cls.bonaberi).ids)], limit=1)
        cls.yaounde = cls.env["res.city"].search(
            [("country_id", "=", cls.env.ref("base.cm").id), ("id", "!=", cls.douala.id)], limit=1)
        cls.company.write({
            "ocd_express_city_ids": [Command.set(cls.douala.ids)],
            "ocd_express_open_to": "invited",
            "ocd_express_cod_rate": 1.5,
            "ocd_express_cod_min": 150,
            "ocd_express_return_fee": 500,
            "ocd_express_pickup_fee": 500,
            "ocd_express_pickup_free_from": 1,
            "ocd_express_cap_new": 50000,
            "ocd_express_cap_confirmed": 200000,
            "ocd_express_cap_after": 20,
            "ocd_express_online_above": 100000,
            "ocd_express_cash_max": 150000,
            "ocd_express_debt_max": 10000,
            "ocd_express_id_daily": 300000,
            "ocd_express_first_day_max": 10,
            "ocd_express_wave1_hour": 10.0,
            "ocd_express_wave2_hour": 15.0,
            "ocd_express_per_courier": 0,
            "ocd_express_shop_share": 20,
            "ocd_express_claim_hours": 48,
            "ocd_express_lost_max": 50000,
            "ocd_express_return_alert": 30,
            "ocd_express_momo_hold_hours": 48,
            "ocd_express_retention_months": 6,
            "ocd_studio_tz": "Africa/Douala",
        })
        Rate = cls.env["ocd.delivery.rate"]
        Rate.search([]).write({"active": False})
        cm = cls.env.ref("base.cm")
        Rate.create({
            "operator": "courier", "origin_city_id": cls.douala.id, "country_id": cm.id,
            "city_ids": [Command.set(cls.douala.ids)], "price": 1000, "allow_cod": True,
        })
        Rate.create({"operator": "agency", "origin_country_id": cm.id, "country_id": cm.id, "price": 2500})
        cls.afi = cls.env["res.partner"].create({
            "name": "Mode Afi",
            "phone": "+237 670112233",
            "country_id": cm.id,
            "city_id": cls.douala.id,
            "district_id": cls.akwa.id,
            "delivery_landmark": "Rue Joss, face a la boulangerie",
            "ocd_express_state": "active",
            "ocd_express_since": datetime(2026, 11, 2).date(),
            "ocd_payout_momo": "+237 670112233",
        })

    def _data(self, **values):
        data = {
            "name": "Grace Mbia",
            "phone": "+237 691234567",
            "district": self.makepe,
            "city": self.douala,
            "landmark": "Face au terrain de foot",
            "content": "2 robes wax",
            "prepaid": False,
            "amount": 15000,
            "value": 0,
            "fee_by": "sender",
            "can_open": True,
            "consent": True,
            "dropoff": False,
        }
        data.update(values)
        return data

    def _create(self, sender=None, **values):
        return self.env["stock.picking"]._ocd_express_create(sender or self.afi, self._data(**values))

    def _pick(self, parcels):
        for pickup in parcels.ocd_express_pickup_id:
            pickup._ocd_done(pickup.parcel_ids & parcels)

    def _deliver(self, parcel, method="cash"):
        if parcel.ocd_stage == "ready":
            self._pick(parcel)
        parcel.action_ocd_leave()
        if parcel.ocd_cod_state == "to_collect":
            parcel._ocd_collect(method, parcel.ocd_courier_id)
        delivered, _left = parcel._ocd_check_code(parcel.sudo().ocd_delivery_code)
        self.assertTrue(delivered)

    def _remit(self, courier, amount=None):
        remittance = self.env["ocd.cash.remittance"]._ocd_open_for(courier)
        remittance.amount_received = remittance.amount_expected if amount is None else amount
        remittance.action_done()
        return remittance

    def _moves(self, parcel, kind=None):
        moves = parcel.ocd_vendor_bill_ids
        return moves.filtered(lambda m: m.ocd_express_kind == kind) if kind else moves
