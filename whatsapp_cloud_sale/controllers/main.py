from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleWhatsApp(WebsiteSale):

    def _parse_form_data(self, form_data):
        """Override of `portal` to store the WhatsApp consent of the checkout address form."""
        shown = form_data.pop("whatsapp_opt_in_shown", None)
        opt_in = form_data.pop("whatsapp_opt_in", None)
        address_values, extra_form_data = super()._parse_form_data(form_data)
        if shown:
            address_values["whatsapp_opt_in"] = bool(opt_in)
        return address_values, extra_form_data
