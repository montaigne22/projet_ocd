from odoo import fields, models


class WhatsappAccount(models.Model):
    _inherit = "whatsapp.account"

    assignment_mode = fields.Selection(
        selection_add=[("salesperson", "Salesperson of the customer")],
        ondelete={"salesperson": "set default"},
        help="Taken by an agent: all the agents see the new conversation, the first one who "
        "answers (or takes it) handles it. Each agent in turn: the conversation goes to the "
        "agent with the fewest open conversations, online agents first. Salesperson of the "
        "customer: the salesperson of their latest order when they are an agent, else each "
        "agent in turn.",
    )
    review_url = fields.Char(
        string="Review Link",
        help="Sent to the customers who rate their order 4 or 5 out of 5 (e.g. the Google "
        "review link of the store).",
    )

    def _get_default_bot_options(self):
        return [{
            "sequence": 1,
            "name": self.env._("Track my order"),
            "description": self.env._("Status of your recent orders"),
            "action": "order_status",
        }, {
            "sequence": 2,
            "name": self.env._("Pay my order"),
            "description": self.env._("Payment link of your orders to pay"),
            "action": "pay",
            "active": False,
        }, {
            "sequence": 20,
            "name": self.env._("Our stores"),
            "description": self.env._("Addresses, opening hours and map"),
            "action": "stores",
            "active": False,
        }, {
            "sequence": 30,
            "name": self.env._("Delivery fees"),
            "description": self.env._("Prices and delivery methods in your city"),
            "action": "delivery_fees",
            "active": False,
        }] + super()._get_default_bot_options()
