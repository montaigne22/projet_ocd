import re

from odoo import _, models
from odoo.tools import format_amount, format_date

from odoo.addons.whatsapp_cloud.tools import normalize_keyword

# Words of a customer asking for their orders.
ORDER_KEYWORDS = {
    "commande", "commandes", "ma commande", "suivi", "suivi commande", "colis", "livraison",
    "order", "orders", "my order", "tracking", "parcel", "delivery",
}
# Reference of an order in a message: S00012, SO123...
ORDER_REF_RE = re.compile(r"\b([A-Z]{1,5}[-/]?\d{3,})\b", re.IGNORECASE)
MAX_ORDERS = 3


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    # === ORDERS OF THE CUSTOMER === #

    def _whatsapp_get_orders(self, limit=MAX_ORDERS):
        """Latest orders and quotations of the customer of the conversation (and of their
        company)."""
        self.ensure_one()
        partner = self.whatsapp_partner_id
        if not partner or partner.whatsapp_to_identify:
            return self.env["sale.order"]
        return self.env["sale.order"].sudo().search([
            ("partner_id", "child_of", partner.commercial_partner_id.id),
            ("state", "!=", "cancel"),
        ], order="date_order desc, id desc", limit=limit)

    def _whatsapp_get_order_status(self, order):
        """Status of an order, in words of the customer."""
        if order.state in ("draft", "sent"):
            return _("quotation waiting for your confirmation")
        if order.state == "cancel":
            return _("cancelled")
        delivery = order.delivery_status if "delivery_status" in order._fields else False
        pickings = order.picking_ids.filtered(lambda p: p.picking_type_code == "outgoing")
        done = pickings.filtered(lambda p: p.state == "done").sorted("date_done")
        in_store = order.carrier_id.delivery_type == "in_store" if order.carrier_id else False
        if delivery == "full" and done:
            if in_store:
                return _("collected on %s", format_date(self.env, done[-1].date_done))
            return _("shipped on %s", format_date(self.env, done[-1].date_done))
        if delivery in ("partial", "started"):
            return _("partly shipped")
        if in_store and pickings.filtered(lambda p: p.state == "assigned"):
            return _("ready for pickup in store")
        return _("confirmed, being prepared")

    def _whatsapp_format_order(self, order):
        self.ensure_one()
        url = f"{order.get_base_url()}{order.get_portal_url()}"
        return _(
            "%(name)s of %(date)s, %(amount)s: %(status)s\n%(url)s",
            name=order.name,
            date=format_date(self.env, order.date_order),
            amount=format_amount(self.env, order.amount_total, order.currency_id),
            status=self._whatsapp_get_order_status(order),
            url=url,
        )

    def _whatsapp_send_order_status(self, orders=None):
        """Answer the customer with the status of their latest orders (or of the given ones),
        in their language."""
        self.ensure_one()
        channel = self.with_context(lang=self._whatsapp_get_lang())
        orders = orders if orders is not None else channel._whatsapp_get_orders()
        if not orders:
            channel._whatsapp_send_bot_text(channel.env._(
                "We find no order for this WhatsApp number."
            ))
            self._whatsapp_handover()
            return
        lines = [channel.env._("Your orders:") if len(orders) > 1 else channel.env._("Your order:")]
        lines += [channel._whatsapp_format_order(order) for order in orders]
        channel._whatsapp_send_answer("\n\n".join(lines))
        if self.whatsapp_bot_state != "agent":
            self.whatsapp_bot_state = "menu"

    def _whatsapp_bot_answer(self, wa_message, content):
        """An order reference or a question about the orders: their status, at once."""
        if super()._whatsapp_bot_answer(wa_message, content):
            return True
        if not self.whatsapp_account_id.company_id.whatsapp_order_tracking:
            return False
        text = wa_message.body or ""
        references = {ref.upper() for ref in ORDER_REF_RE.findall(text)}
        if references:
            orders = self._whatsapp_get_orders(limit=50).filtered(
                lambda order: order.name.upper().replace("/", "").replace("-", "")
                in {ref.replace("/", "").replace("-", "") for ref in references}
            )
            if orders:
                self._whatsapp_send_order_status(orders)
                return True
        if normalize_keyword(text) in ORDER_KEYWORDS:
            self._whatsapp_send_order_status()
            return True
        return False

    # === SATISFACTION === #

    def _whatsapp_handle_reply(self, wa_message, content):
        """A rating of the customer from the buttons of the satisfaction template."""
        if super()._whatsapp_handle_reply(wa_message, content):
            return True
        order, value = wa_message._whatsapp_get_rating(content.get("reply_id"))
        if not order:
            return False
        self._whatsapp_register_rating(order, value, wa_message)
        return True

    def _whatsapp_register_rating(self, order, value, wa_message):
        """Store the rating on the order, thank the customer, and alert the team when they
        are not satisfied."""
        self.ensure_one()
        rating = order._whatsapp_add_rating(value, wa_message.partner_id)
        account = self.whatsapp_account_id.with_context(lang=self._whatsapp_get_lang())
        channel = self.with_context(lang=self._whatsapp_get_lang())
        if value >= 4:
            text = channel.env._("Thank you very much for your rating, it makes us very happy!")
            if account.review_url:
                text = "\n".join([text, channel.env._(
                    "Would you share your opinion in a few words? %s", account.review_url,
                )])
            channel._whatsapp_send_bot_text(text)
        elif value == 3:
            channel._whatsapp_send_bot_text(channel.env._(
                "Thank you for your rating. Tell us here what we could do better, we read all "
                "the messages."
            ))
        else:
            channel._whatsapp_send_bot_text(channel.env._(
                "We are sorry that your order did not satisfy you. Tell us here what went wrong: "
                "an advisor will answer you to find a solution."
            ))
            self._whatsapp_notify(_(
                "Unsatisfied customer: %(value)s/5 for %(order)s.", value=value, order=order.name,
            ))
            self._whatsapp_handover(invite=False)
        return rating

    # === TEAM === #

    def _whatsapp_get_preferred_user(self, agents):
        """The salesperson of the latest order, when they are an agent."""
        user = super()._whatsapp_get_preferred_user(agents)
        if user or self.whatsapp_account_id.assignment_mode != "salesperson":
            return user
        salesperson = self._whatsapp_get_orders(limit=1).user_id
        if salesperson and salesperson in agents:
            return salesperson
        return self.whatsapp_account_id._pick_agent(agents)

    def _whatsapp_get_placeholder_values(self):
        values = super()._whatsapp_get_placeholder_values()
        order = self._whatsapp_get_orders(limit=1)
        link = f"{order.get_base_url()}{order.get_portal_url()}" if order else ""
        values.update({
            "order": order.name or "", "commande": order.name or "",
            "order_link": link, "lien_commande": link,
        })
        return values

    # === INFORMATION PANEL === #

    def _whatsapp_get_info_sections(self):
        sections = super()._whatsapp_get_info_sections()
        orders = self._whatsapp_get_orders(limit=5)
        ratings = dict(self.env["rating.rating"].sudo()._read_group(
            [("res_model", "=", "sale.order"), ("res_id", "in", orders.ids), ("consumed", "=", True)],
            ["res_id"], ["rating:max"],
        )) if orders else {}
        sections.append({
            "title": _("Orders"),
            "empty": _("No order yet."),
            "items": [{
                "id": order.id,
                "model": "sale.order",
                "name": order.name,
                "detail": " · ".join(filter(None, [
                    format_date(self.env, order.date_order),
                    format_amount(self.env, order.amount_total, order.currency_id),
                    self._whatsapp_get_order_status(order),
                    _("rated %s/5", int(ratings[order.id])) if ratings.get(order.id) else "",
                ])),
            } for order in orders],
            "buttons": [{"name": _("New Quotation"), "method": "whatsapp_action_new_quotation"}],
        })
        return sections

    def whatsapp_action_new_quotation(self):
        """A quotation for the customer of the conversation, to send them from it."""
        self._whatsapp_check_agent()
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
            "context": {
                "default_partner_id": self.whatsapp_partner_id.id,
                "default_origin": _("WhatsApp"),
            },
        }
