from odoo import SUPERUSER_ID, api

# The low stock alert (chantier 21) sends the template of the plan (ocd_stock_bas, already
# submitted to Meta) for a colour and a size: the pieces and the choice come from the sending.
NEW_VALUES = {
    "{{ object._ocd_free_total() }}": "{{ ctx.get('ocd_low_qty') or object._ocd_free_total() }}",
    "{{ object.name }}": "{{ ctx.get('ocd_low_name') or object.name }}",
}


def migrate(cr, version):
    """The values of the template ocd_stock_bas (kept by the module update), and no second
    template of the same name (written for a while on the branch of chantier 21)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid in ("ocd_live_shop_whatsapp.template_stock_low", "ocd_live_shop_whatsapp.template_stock_low_en"):
        template = env.ref(xmlid, raise_if_not_found=False)
        if not template:
            continue
        for variable in template.variable_ids.filtered(lambda variable: variable.sequence in (2, 3)):
            if variable.value in NEW_VALUES:
                variable.value = NEW_VALUES[variable.value]
    for xmlid in ("ocd_live_shop_whatsapp.template_low_stock", "ocd_live_shop_whatsapp.template_low_stock_en"):
        duplicate = env.ref(xmlid, raise_if_not_found=False)
        if duplicate:
            duplicate.unlink()
