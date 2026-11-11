from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_amount


class SaleOrder(models.Model):
    _inherit = "sale.order"

    whatsapp_quotation = fields.Boolean(related="company_id.whatsapp_quotation")

    def _whatsapp_get_channel(self):
        """The WhatsApp conversation of the customer of the order, if any."""
        self.ensure_one()
        partner = self.partner_id
        number = partner._whatsapp_number()
        if not number and not partner.whatsapp_user_ref:
            return self.env["discuss.channel"]
        Account = self.env["whatsapp.account"].sudo()
        accounts = Account.search([("company_id", "=", self.company_id.id)]) or (
            Account._get_default_account(self.company_id)
        )
        if not accounts:
            return self.env["discuss.channel"]
        # the conversation where the customer wrote last, whatever the number they wrote to
        return self.env["discuss.channel"].sudo()._whatsapp_find(
            accounts, number, partner.whatsapp_user_ref
        )

    def _whatsapp_add_rating(self, value, partner):
        """Store the rating (1 to 5) given by the customer on WhatsApp."""
        self.ensure_one()
        rating = self.env["rating.rating"].sudo().create({
            "res_model_id": self.env["ir.model"]._get_id("sale.order"),
            "res_id": self.id,
            "partner_id": partner.id,
            "rated_partner_id": self.user_id.partner_id.id,
            "rating": value,
            "consumed": True,
            "feedback": _("Rating given on WhatsApp."),
        })
        self.sudo().message_post(
            body=Markup("%s") % _("Rating of the customer on WhatsApp: %s/5", value),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return rating

    def _whatsapp_get_amount_to_pay(self):
        """Amount the customer can pay online now: the prepayment of a sent quotation, the
        rest of a confirmed order."""
        self.ensure_one()
        order = self.sudo()
        if order.state == "sent" and not order.is_expired:
            return order._get_default_payment_link_values()["amount"]
        if order.state == "sale":
            return order.amount_unpaid
        return 0.0

    def _whatsapp_get_payment_link(self, amount):
        """Link to pay the amount online on the page of the order (no login needed)."""
        self.ensure_one()
        wizard = self.env["payment.link.wizard"].sudo().with_context(
            active_model="sale.order", active_id=self.id
        ).create({"amount": amount})
        return wizard.link

    def action_whatsapp_send_quotation(self):
        """Send the quotation on WhatsApp with its link, to view and pay it online: as an
        answer in the conversation when the customer wrote within 24 hours, else with the
        "quotation_sent" template."""
        self.ensure_one()
        if not self.whatsapp_quotation:
            raise UserError(_(
                "The quotations on WhatsApp are disabled in the settings (WhatsApp section)."
            ))
        if self.state not in ("draft", "sent"):
            raise UserError(_("Only a quotation can be sent this way."))
        channel = self._whatsapp_get_channel()
        if channel and channel._whatsapp_is_window_open():
            url = f"{self.get_base_url()}{self.get_portal_url()}"
            lang = channel._whatsapp_get_lang()
            text = self.with_context(lang=lang).env._(
                "Hello %(name)s, here is your quotation %(order)s for %(amount)s. You can view "
                "it and pay it online: %(url)s",
                name=(self.partner_id.name or "").split(" ")[0],
                order=self.name,
                amount=format_amount(self.env, self.amount_total, self.currency_id),
                url=url,
            )
            # the salesperson joins the conversation to write in it
            channel.sudo()._whatsapp_add_users(self.env.user)
            channel.with_user(self.env.user).message_post(
                body=Markup("%s") % text, message_type="comment", subtype_xmlid="mail.mt_comment",
            )
            if self.state == "draft":
                self.action_quotation_sent()
            self.message_post(body=_("Quotation sent on WhatsApp."), subtype_xmlid="mail.mt_note")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {"message": _("Quotation sent on WhatsApp."), "type": "success",
                           "next": {"type": "ir.actions.act_window_close"}},
            }
        template = self.env.ref(
            "whatsapp_cloud_sale.template_quotation_sent", raise_if_not_found=False
        )
        if self.state == "draft":
            self.action_quotation_sent()
        return {
            "type": "ir.actions.act_window",
            "name": _("Send WhatsApp"),
            "res_model": "whatsapp.composer",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": "sale.order",
                "default_res_ids": self.ids,
                "default_template_id": template.id if template else False,
                "whatsapp_channel_id": channel.id,
            },
        }
