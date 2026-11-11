from odoo import SUPERUSER_ID, api

# Link button "Track my order" of the templates provided without it before.
BUTTON_URLS = {
    "template_order_ready_for_pickup": "{{ object.get_portal_url() }}",
    "template_order_ready_for_pickup_en": "{{ object.get_portal_url() }}",
    "template_order_shipped": "{{ object.sale_id and object.sale_id.get_portal_url() or '' }}",
    "template_order_shipped_en": "{{ object.sale_id and object.sale_id.get_portal_url() or '' }}",
}


def migrate(cr, version):
    """The templates are "noupdate": give the link of the order to the ones without it. As
    the ones already synchronised, they send it until the next synchronisation reads at
    Meta whether their button expects it."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid, url in BUTTON_URLS.items():
        template = env.ref(f"whatsapp_cloud_sale.{xmlid}", raise_if_not_found=False)
        if template and not template.button_url_value:
            template.write({"button_url_value": url, "button_url_dynamic": True})
