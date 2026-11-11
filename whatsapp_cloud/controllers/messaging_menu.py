from odoo.fields import Domain

from odoo.addons.mail.controllers.discuss.messaging_menu import DiscussMessagingMenuController


class WhatsappMessagingMenuController(DiscussMessagingMenuController):
    """WhatsApp tab of the messaging menu: the conversations of the agent, and the ones not
    assigned yet (visible to all the agents)."""

    def _get_menu_tab_domain(self, tab_id):
        if tab_id == "whatsapp":
            return Domain("channel_type", "=", "whatsapp") & (
                Domain("self_member_id.is_pinned", "=", True)
                | (Domain("whatsapp_user_id", "=", False) & Domain("whatsapp_state", "!=", "done"))
            )
        return super()._get_menu_tab_domain(tab_id)

    def _get_menu_tab_filter_domain(self, tab_id, filter_id):
        match (tab_id, filter_id):
            case ("whatsapp", "whatsapp_unread"):
                return Domain("self_member_id.is_unread", "=", True)
            case ("whatsapp", "whatsapp_mine"):
                return Domain("whatsapp_user_id", "=", self.env.user.id)
            case ("whatsapp", "whatsapp_unassigned"):
                return Domain("whatsapp_user_id", "=", False) & Domain("whatsapp_state", "!=", "done")
            case ("whatsapp", "whatsapp_waiting"):
                return Domain("whatsapp_waiting_since", "!=", False)
        return super()._get_menu_tab_filter_domain(tab_id, filter_id)
