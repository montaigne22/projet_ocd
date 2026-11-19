import logging

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _ocd_process_confirmed_lines(self):
        """Override of `ocd_live`: a line of OCD Business paid gives its period (once), and the
        order its invoice."""
        result = super()._ocd_process_confirmed_lines()
        Period = self.env["ocd.business.period"].sudo()
        for line in self.sudo().filtered(lambda l: l.product_id.ocd_product_kind == "business"):
            period = Period._ocd_from_line(line)
            if not period:
                continue  # already given (a second confirmation of the same payment)
            line.order_id._ocd_business_invoice()
            period.vendor_id._ocd_business_tell("paid")
        return result


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _ocd_business_lines(self):
        return self.order_line.filtered(lambda line: line.product_id.ocd_product_kind == "business")

    def _ocd_business_invoice(self):
        """One invoice per payment of OCD Business, posted, joined to the payment of the order
        (paid online): « My invoices » and the accounting. Without accounting set up, the period
        stays and the team is told in the order."""
        for order in self.sudo().filtered(lambda o: not o.invoice_ids):
            try:
                with self.env.cr.savepoint():
                    invoice = order._create_invoices()
                    invoice.action_post()
                    transactions = order.transaction_ids.filtered(lambda tx: tx.state in ("done", "authorized"))
                    if transactions:
                        transactions.invoice_ids = [(4, invoice.id)]
            except UserError as exc:
                _logger.warning("No invoice for the order %s of OCD Business: %s", order.name, exc)
                order.message_post(body=self.env._("The invoice could not be made: %s", exc.args[0]))

    def _ocd_announce_payment(self, reference):
        """Override of `ocd_live`: « I paid » for OCD Business keeps the features of the vendor
        the days of grace, the time of the check."""
        result = super()._ocd_announce_payment(reference)
        for order in self.filtered(lambda o: o._ocd_business_lines()):
            order.partner_id.commercial_partner_id._ocd_business_grace(order)
        return result

    def _action_cancel(self):
        """An order of OCD Business cancelled after it was paid (refunded): the days not passed
        yet are taken back; a payment refused ends the grace."""
        result = super()._action_cancel()
        Period = self.env["ocd.business.period"].sudo()
        for order in self.sudo().filtered(lambda o: o._ocd_business_lines()):
            periods = Period.search([("sale_order_id", "=", order.id)])
            if periods:
                periods._ocd_cancel(self.env._("Order %s cancelled", order.name))
            else:
                order.partner_id.commercial_partner_id.ocd_business_grace_until = False
        return result
