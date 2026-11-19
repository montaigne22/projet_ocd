from odoo import fields


def post_init_hook(env):
    """The dates of OCD Business typed by hand before this module become periods offered: « until »
    is then read from the periods only, and nothing is lost."""
    Period = env["ocd.business.period"].sudo()
    today = fields.Date.context_today(Period)
    for vendor in env["res.partner"].sudo().search([("ocd_business_until", ">=", today)]):
        if Period.search_count([("vendor_id", "=", vendor.id)]):
            continue
        Period.create({
            "vendor_id": vendor.id,
            "company_id": (vendor.company_id or env.company).id,
            "kind": "offered",
            "date_start": today,
            "date_end": vendor.ocd_business_until,
            "days": (vendor.ocd_business_until - today).days + 1,
            "state": "active",
            "note": env._("Set by hand before OCD Business"),
        })
    for vendor in env["res.partner"].sudo().search([("ocd_business_until", "!=", False),
                                                    ("ocd_business_until", "<", today)]):
        # An end already passed stays as it was (no period to give)
        vendor.ocd_business_end_told_for = vendor.ocd_business_until
