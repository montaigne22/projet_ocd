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


def restore_english_templates(env):
    """The English versions of the templates of the WhatsApp modules, archived by the version
    20.0.1.4.0 of this module (French only), are active again: the English-speaking contacts
    receive them once Meta approved them."""
    data = env["ir.model.data"].sudo().search([
        ("model", "=", "whatsapp.template"), ("module", "in", WHATSAPP_MODULES),
    ])
    templates = env["whatsapp.template"].sudo().with_context(active_test=False).browse(data.mapped("res_id")).exists()
    english = templates.filtered(lambda template: not template.active and template._lang_base(template.lang_code) == "en")
    if english:
        english.active = True
    return english


def post_init_hook(env):
    align_whatsapp_consent(env)
