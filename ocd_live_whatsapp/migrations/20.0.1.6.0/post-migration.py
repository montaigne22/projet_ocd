from odoo import SUPERUSER_ID, api

# The end of the window of the directory, in the time of the vendor (was the studio's)
OLD_WINDOW_END = "object.company_id._ocd_to_local(object.window_end)"
NEW_WINDOW_END = "object.partner_id._ocd_to_local(object.window_end)"
TICKETS = ("ocd_live_whatsapp.template_ticket", "ocd_live_whatsapp.template_ticket_en")
WINDOWS = ("ocd_live_whatsapp.template_link_online", "ocd_live_whatsapp.template_link_online_en")


def migrate(cr, version):
    """The ticket comes with its PDF: the ticket templates not approved by Meta take the PDF in
    their header (an approved one keeps the text Meta knows: the team adds the PDF, then submits
    it again). The variables that gave the hours of the studio give the ones of the vendor."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Template = env["whatsapp.template"]
    Template._cron_read_pending_from_meta()
    report = env.ref("ocd_live.action_report_ticket", raise_if_not_found=False)
    for xmlid in TICKETS:
        template = env.ref(xmlid, raise_if_not_found=False)
        if report and template and template.status in ("unknown", "rejected") and template.header_type == "none":
            template.write({"header_type": "document", "header_report_id": report.id})
    for xmlid in WINDOWS:
        template = env.ref(xmlid, raise_if_not_found=False)
        for variable in template.variable_ids if template else []:
            if OLD_WINDOW_END in (variable.value or ""):
                variable.value = variable.value.replace(OLD_WINDOW_END, NEW_WINDOW_END)
