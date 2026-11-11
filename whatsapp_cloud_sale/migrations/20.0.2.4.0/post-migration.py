from odoo import SUPERUSER_ID, api

# The previous texts of the templates of the module, refused by Meta: they ended with a
# variable ("({{4}})." is a variable at the end for Meta).
OLD_TEXTS = {
    "whatsapp_cloud_sale.template_order_received": [
        "Bonjour {{1}}, nous avons bien reçu votre commande {{2}} d'un montant de {{3}}. Elle sera "
        "confirmée dès réception de votre paiement ({{4}}).",
    ],
    "whatsapp_cloud_sale.template_order_received_en": [
        "Hello {{1}}, we have received your order {{2}} for {{3}}. It will be confirmed as soon as "
        "your payment is received ({{4}}).",
    ],
}


def migrate(cr, version):
    """The templates not approved by Meta yet, with a previous text of the module, take the
    new one: the template data is loaded only at the installation."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["whatsapp.template"]._update_module_texts("whatsapp_cloud_sale", OLD_TEXTS)
