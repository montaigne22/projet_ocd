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


def post_init_hook(env):
    align_whatsapp_consent(env)
