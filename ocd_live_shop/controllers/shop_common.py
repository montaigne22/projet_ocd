"""What the pages of the shop show of a product: price for the visitor, photo, stock, sale mode.
Shared by the shop, the product page, the cart and the boutique of a vendor."""
from odoo.http import request

from odoo.addons.ocd_live.controllers import common

LOW_STOCK = 3


def currency():
    pricelist = getattr(request, "pricelist", None)
    return (pricelist and pricelist.currency_id) or request.env.website.currency_id


def prices(templates):
    """Return {template id: price written for the visitor}, with the pricelist and the taxes of
    the website, as the shop of Odoo computes them."""
    templates = templates.sudo()
    if not templates:
        return {}
    website = request.env.website
    pricelist = getattr(request, "pricelist", None) or website.pricelist_id
    fiscal_position = getattr(request, "fiscal_position", None) or request.env["account.fiscal.position"]
    values = templates._get_sales_prices(pricelist, fiscal_position, website)
    money_currency = currency()
    return {
        t.id: common.money(values.get(t.id, {}).get("price_reduce", t.list_price), money_currency)
        for t in templates
    }


def variant_price(product):
    """Price of a variant for the visitor, as on the product page of Odoo: (amount, currency)."""
    info = product.sudo()._get_combination_info_variant()
    return info["price"], info["currency"]


def tracked(product):
    """Whether the stock of the product (template or variant) limits the sales."""
    return bool(product.is_storable and not product.allow_out_of_stock_order)


def free_qty(variant):
    return int(request.env.website._get_product_available_qty(variant.sudo()))


def stock_info(template):
    """Return (sold out, "Only N left" or False) for the cards of the products."""
    template = template.sudo()
    if not tracked(template):
        return False, False
    qty = sum(free_qty(variant) for variant in template.product_variant_ids)
    if qty <= 0:
        return True, False
    if qty <= LOW_STOCK:
        return False, request.env._("Only %s left", qty)
    return False, False


def image_url(template, size="image_512"):
    return f"/web/image/product.template/{template.id}/{size}" if template.sudo().image_128 else False


def sold_by_ocd(template):
    """Whether OCD sells the product (sold and delivered by OCD Live): products of a vendor in
    direct contact are not sold on the website, they open WhatsApp."""
    vendor = template.sudo().ocd_vendor_id
    return not vendor or vendor.ocd_sale_mode == "ocd"


def vendor_line(template):
    vendor = template.sudo().ocd_vendor_id
    if not vendor:
        return request.env.company.name
    return " · ".join(part for part in (vendor.name, vendor.city) if part)


def card(template, price_by_id):
    """One product in a grid of products (shop, boutique)."""
    out, low = stock_info(template)
    ocd = sold_by_ocd(template)
    return {
        "product": template,
        "url": template.website_url,
        "price": price_by_id.get(template.id) or common.money(template.list_price, template.currency_id),
        "image": image_url(template),
        "out": out,
        "low": low,
        "by": vendor_line(template),
        "ocd": ocd,
        "mode": request.env._("Delivered by OCD") if ocd else request.env._("Direct contact with the vendor"),
    }
