from datetime import timedelta

from odoo import Command, fields
from odoo.tests import TransactionCase


def pending_payment(test, order, provider=None):
    """A payment checked by the team (Mobile Money to the number of OCD) chosen on the page of
    the order: the transaction waits, nothing was sent yet."""
    provider = provider or test.env["payment.provider"].search([
        ("code", "=", "custom"), ("company_id", "=", order.company_id.id),
    ], limit=1)
    if not provider.payment_method_ids:
        test.skipTest("No payment provider checked by the team in this database.")
    transaction = test.env["payment.transaction"].create({
        "provider_id": provider.id,
        "payment_method_id": provider.payment_method_ids[:1].id,
        "amount": order.amount_total,
        "currency_id": order.currency_id.id,
        "partner_id": order.partner_id.id,
        "reference": f"{order.name}-T",
        "sale_order_ids": [Command.set(order.ids)],
    }).with_context(payment_safe_write=True)
    transaction._set_pending()
    return transaction


class OcdLiveCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True, mail_notrack=True))
        cls.company = cls.env.company
        cls.company.write({
            "ocd_booking_open_date": fields.Date.today() - timedelta(days=1),
            "ocd_studio_tz": "Africa/Lome",
            "ocd_first_slot_hour": 8.5,
            "ocd_slot_hours": 1.5,
            "ocd_slots_per_day": 9,
            "ocd_min_notice_hours": 2,
            "ocd_hold_minutes": 30,
            "ocd_require_animatrice": True,
            "ocd_live_responsible_id": cls.env.ref("base.user_admin").id,
            "ocd_lives_channel_id": cls.env.ref("ocd_live.channel_lives").id,
        })
        cls.vendor = cls.env["res.partner"].create({
            "name": "Brenda Wax",
            "ocd_is_vendor": True,
            "ocd_business": "Clothes in wax",
            "ocd_vendor_state": "approved",
            "country_id": cls.env.ref("base.cm").id,
            "phone": "+237 670000002",
        })
        cls.other_vendor = cls.env["res.partner"].create({
            "name": "Fatou Karite",
            "ocd_is_vendor": True,
            "ocd_business": "Shea butter",
            "ocd_vendor_state": "approved",
            "country_id": cls.env.ref("base.tg").id,
        })
        cls.discovery = cls.env.ref("ocd_live.product_package_discovery").product_variant_id
        cls.duo = cls.env.ref("ocd_live.product_package_duo").product_variant_id
        cls.four_hours = cls.env.ref("ocd_live.product_package_four_hours").product_variant_id
        cls.monthly = cls.env.ref("ocd_live.product_package_monthly").product_variant_id
        cls.pass_product = cls.env.ref("ocd_live.product_directory_pass").product_variant_id
        cls.host = cls.env["hr.employee"].create({"name": "Dzifa A.", "ocd_is_animatrice": True})
        # A day far enough in the future, so that every slot is bookable
        cls.day = fields.Date.today() + timedelta(days=10)
        cls.starts = cls.company._ocd_slot_starts(cls.day)

    @classmethod
    def _book(cls, start, partner=None, product=None, mode="studio", state="draft", **vals):
        product = product or cls.discovery
        return cls.env["ocd.live.booking"].create({
            "partner_id": (partner or cls.vendor).id,
            "start_datetime": start,
            "slot_count": product.ocd_slot_count,
            "product_id": product.id,
            "mode": mode,
            "state": state,
            **vals,
        })

    @classmethod
    def _sell(cls, product, partner=None):
        """Create and confirm the order of `product`, as the payment provider would."""
        order = cls.env["sale.order"].create({
            "partner_id": (partner or cls.vendor).id,
            "order_line": [fields.Command.create({"product_id": product.id, "product_uom_qty": 1})],
        })
        order.action_confirm()
        return order
