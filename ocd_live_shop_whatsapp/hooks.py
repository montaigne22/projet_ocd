def align_shop_consent(env):
    """The customers of the shop who did not refuse at the checkout (box of OCD Live) agree for
    WhatsApp too, unless they answered STOP."""
    orders = env["sale.order"].sudo().search([("picking_ids.ocd_is_parcel", "=", True)])
    customers = orders.partner_id.filtered(
        lambda partner: partner.ocd_whatsapp_optin and not partner.whatsapp_opt_in and not partner.whatsapp_opt_out
    )
    if customers:
        customers.write({"whatsapp_opt_in": True})


def post_init_hook(env):
    align_shop_consent(env)
