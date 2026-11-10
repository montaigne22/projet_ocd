from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.ocd_live.controllers import common
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.portal import PaymentPortal


class OcdParcelPayment(PaymentPortal):
    """Payment of a parcel at the door, on the phone of the customer, opened from the QR code
    shown by the courier. The page shows the payment form of Odoo: it offers the providers and
    methods that take the country of the customer, the currency and the amount, as configured
    by the team. Nothing here depends on a provider."""

    def _ocd_parcel(self, picking_id, access_token):
        parcel = request.env["stock.picking"].sudo().browse(picking_id).exists()
        if (
            not parcel
            or not parcel.ocd_is_parcel
            or not access_token
            or not payment_utils.check_access_token(access_token, parcel.id, parcel.ocd_cod_amount)
        ):
            raise request.not_found()
        return parcel

    @http.route("/ocd/colis/<int:picking_id>/payer", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def parcel_pay(self, picking_id, access_token=None, **kwargs):
        parcel = self._ocd_parcel(picking_id, access_token)
        env = request.env
        currency = parcel.ocd_currency_id
        total = common.money(parcel.ocd_cod_amount, currency)
        last = env["payment.transaction"].sudo().search([("ocd_picking_id", "=", parcel.id)], order="id desc", limit=1)
        if parcel.ocd_cod_state != "to_collect":
            state = "done"
        elif last.state in ("pending", "authorized", "done"):
            state = "waiting"
        elif last.state in ("error", "cancel"):
            state = "failed"
        else:
            state = "form"
        values = {
            "parcel": parcel,
            "state": state,
            "tx": last,
            "total": total,
            "country": parcel.partner_id.country_id,
            "access_token": access_token,
        }
        if state in ("form", "failed"):
            values.update(self._prepare_payment_form_values(
                parcel.company_id.id, parcel.partner_id.id, parcel.ocd_cod_amount, currency_id=currency.id,
            ))
            values.update({
                "amount": parcel.ocd_cod_amount,
                "currency": currency,
                "partner_id": parcel.partner_id.id,
                "transaction_route": f"/ocd/colis/{parcel.id}/transaction",
                "landing_route": f"/ocd/colis/{parcel.id}/payer?access_token={access_token}",
                "submit_button_label": env._("Pay %s", total),
                "show_amount_input": False,
            })
        return request.render("ocd_live_shop.parcel_pay", common.page_values(False, **values))

    @http.route("/ocd/colis/<int:picking_id>/transaction", type="jsonrpc", auth="public")
    def parcel_transaction(self, picking_id, access_token, **kwargs):
        """Create the transaction of the parcel: the amount and the customer come from the
        parcel, never from the browser."""
        parcel = self._ocd_parcel(picking_id, access_token)
        if parcel.ocd_cod_state != "to_collect":
            raise ValidationError(request.env._("This parcel is already paid."))
        self._validate_transaction_kwargs(kwargs)
        kwargs.update({
            "amount": parcel.ocd_cod_amount,
            "currency_id": parcel.ocd_currency_id.id,
            "partner_id": parcel.partner_id.id,
        })
        transaction = self._create_transaction(custom_create_values={"ocd_picking_id": parcel.id}, **kwargs)
        return transaction._get_processing_values()
