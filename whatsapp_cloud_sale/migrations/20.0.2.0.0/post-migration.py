from odoo import SUPERUSER_ID, api
from odoo.fields import Command

# Examples of the variables, for the submission of the templates to Meta from Odoo.
SAMPLES = {
    "template_order_received": ["Awa", "S00012", "25 000 FCFA", "Virement bancaire"],
    "template_order_received_en": ["Awa", "S00012", "25,000 FCFA", "Bank transfer"],
    "template_order_confirmed": ["Awa", "S00012", "25 000 FCFA"],
    "template_order_confirmed_en": ["Awa", "S00012", "25,000 FCFA"],
    "template_order_ready_for_pickup": ["Awa", "S00012", "Boutique du centre"],
    "template_order_ready_for_pickup_en": ["Awa", "S00012", "City centre store"],
    "template_order_shipped": ["Awa", "S00012", "Livraison Douala"],
    "template_order_shipped_en": ["Awa", "S00012", "Douala delivery"],
}


def migrate(cr, version):
    """The templates are "noupdate": give them examples and their "Track my order" button
    (unless already read from Meta). The accounts get the "Track my order" option."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid, samples in SAMPLES.items():
        template = env.ref(f"whatsapp_cloud_sale.{xmlid}", raise_if_not_found=False)
        if not template:
            continue
        for variable, sample in zip(template.variable_ids.sorted("sequence"), samples):
            if not variable.sample_value:
                variable.sample_value = sample
        if not template.button_ids and not template.wa_template_id and template.status == "unknown":
            label = "Track my order" if xmlid.endswith("_en") else "Suivre ma commande"
            template.button_ids = [Command.create({
                "button_type": "url", "name": label, "url": "{base_url}/{{1}}",
                "url_example": "/my/orders/12?access_token=abc123",
            })]
    for account in env["whatsapp.account"].with_context(active_test=False).search([]):
        if not account.bot_option_ids.filtered(lambda option: option.action == "order_status"):
            account._create_default_bot_options(actions={"order_status"})
