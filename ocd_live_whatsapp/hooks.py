def align_whatsapp_consent(env):
    """One consent for OCD Live and WhatsApp:

    - a refusal kept by OCD Live (box unticked, switch off) is a refusal for WhatsApp too;
    - the vendors who did not refuse agreed through OCD Live (booking form, vendor space, the
      team): they agree for WhatsApp too, unless they answered STOP.
    """
    Partner = env["res.partner"].sudo().with_context(active_test=False)
    refused = Partner.search([("ocd_whatsapp_optin", "=", False), ("whatsapp_opt_out", "=", False)])
    if refused:
        refused.write({"whatsapp_opt_in": False})
    agreed = Partner.search([
        ("ocd_is_vendor", "=", True),
        ("ocd_whatsapp_optin", "=", True),
        ("whatsapp_opt_in", "=", False),
        ("whatsapp_opt_out", "=", False),
    ])
    if agreed:
        agreed.write({"whatsapp_opt_in": True})


# Modules that give versions of their templates in English, besides the French ones
WHATSAPP_MODULES = ("whatsapp_cloud", "whatsapp_cloud_sale")


def archive_english_templates(env):
    """OCD Live writes to its vendors, couriers and customers in French: the English versions of
    the templates given by the WhatsApp modules are archived. They are never sent (a contact
    whose language is English gets the French version), are out of the lists and are not to
    submit to Meta; the team can bring one back (filter « Archived »). The data of the modules
    is loaded once, so an update does not bring them back."""
    data = env["ir.model.data"].sudo().search([
        ("model", "=", "whatsapp.template"), ("module", "in", WHATSAPP_MODULES),
    ])
    templates = env["whatsapp.template"].sudo().browse(data.mapped("res_id")).exists()
    english = templates.filtered(lambda template: template.active and template._lang_base(template.lang_code) == "en")
    if english:
        english.active = False
    return english


def post_init_hook(env):
    align_whatsapp_consent(env)
    archive_english_templates(env)
