import threading
from collections import OrderedDict
from urllib.parse import urlsplit

from odoo import fields, http
from odoo.http import request

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common

from .. import share_image
from . import shop_common

# The last images drawn, kept by this process: a share or a catalogue opened again is not drawn
# again (the address of an image changes with its products, the CDN keeps it too)
_DRAWN = OrderedDict()
_DRAWN_MAX = 48
_DRAWN_LOCK = threading.Lock()
# A year, for an address that changes with what the image shows
IMMUTABLE = "public, max-age=31536000, immutable"
# Copies of each price label: a sheet of A4 holds 24
LABELS_MAX_COPIES = 24
# Characters of a price written at full size on a label
LABEL_PRICE_SHORT = 9


def drawn(key, draw):
    """The image `key`, drawn by `draw()` only when it is not kept yet."""
    with _DRAWN_LOCK:
        data = _DRAWN.get(key)
        if data is not None:
            _DRAWN.move_to_end(key)
            return data
    data = draw()
    with _DRAWN_LOCK:
        _DRAWN[key] = data
        while len(_DRAWN) > _DRAWN_MAX:
            _DRAWN.popitem(last=False)
    return data


def short_link(url):
    """The address without "https://", as people write it."""
    parts = urlsplit(url)
    return f"{parts.netloc}{parts.path}".rstrip("/")


def photo_bytes(product, size="image_1024"):
    value = product.sudo()[size]
    return bytes(value) if value else None


def jpeg_response(data, unique, stamp):
    return request.make_response(data, headers=[
        ("Content-Type", "image/jpeg"),
        ("Cache-Control", IMMUTABLE if unique == stamp else "public, max-age=3600"),
    ])


class OcdVendorShare(http.Controller):
    """What a vendor shares on their WhatsApp status: the image of a product (1.3 of the plan of
    « My products ») and the catalogue of their boutique (1.7). And what they print for their
    store: the price labels with the QR code of each product (M.7)."""

    # === ONE PRODUCT === #

    @http.route("/ocd/produit/<int:product_id>/partage.jpg", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def product_image(self, product_id, unique=None, **kwargs):
        """The image of a product on sale, to share: its photo, its name, its price and the QR
        code of its page. Public, like the page of the product."""
        product = request.env["product.template"].sudo().browse(product_id).exists()
        if not product or not product.is_published or product.ocd_review_state != "approved":
            raise request.not_found()
        env = request.env
        stamp = product._ocd_photo_stamp(product)
        url = request.httprequest.url_root.rstrip("/") + product.website_url
        lang = env.lang or ""
        data = drawn(("product", product.id, stamp, lang, url), lambda: share_image.product({
            "photo": photo_bytes(product),
            "name": product.name,
            "price": common.money(product.list_price, product.currency_id),
            "vendor": product.ocd_vendor_id.name or common.company().name,
            "cta": env._("Order it on OCD Live"),
            "link": short_link(url),
            "url": url,
        }))
        return jpeg_response(data, unique, stamp)

    @http.route("/ocd/espace/moi/partage", type="http", auth="public", website=True, methods=["POST"], csrf=False,
                sitemap=False)
    def shared(self, **kwargs):
        """Told by the phone when the vendor shared their boutique, a product or their catalogue
        (a beacon: no form, so no token; it only marks a first step done in their space)."""
        vendor = common.current_vendor()
        if vendor and not vendor.ocd_shared_at:
            vendor.sudo().ocd_shared_at = fields.Datetime.now()
        return request.make_response("", status=204)

    # === THE CATALOGUE OF THE BOUTIQUE === #

    def _catalogue(self, vendor):
        """(products on sale in the order of the boutique, stamp of the catalogue, pages)."""
        company = common.company()
        products = request.env["product.template"]._ocd_vendor_products(vendor).filtered(
            lambda p: p.is_published and p.ocd_review_state == "approved"
        )
        free = products.product_variant_ids._ocd_free_qties()
        products = products.filtered(
            lambda p: not shop_common.tracked(p) or any(free[v.id] > 0 for v in p.product_variant_ids)
        )
        per_page = min(max(company.ocd_vendor_catalogue_items or share_image.CATALOGUE_ITEMS, 1),
                       share_image.CATALOGUE_ITEMS)
        # As many images as needed, the products spread evenly: 5 products give 2 + 3, not 4 + 1
        count = -(-len(products) // per_page)
        bounds = [round(len(products) * index / count) for index in range(count + 1)] if count else []
        pages = [products[bounds[index]:bounds[index + 1]] for index in range(count)]
        latest = max((p.write_date for p in products), default=None)
        stamp = f"{latest:%Y%m%d%H%M%S}-{len(products)}-{per_page}" if latest else "0"
        return products, stamp, pages

    @http.route("/ocd/espace/moi/catalogue", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def catalogue(self, **kwargs):
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        products, stamp, pages = self._catalogue(vendor)
        images = [f"/ocd/espace/moi/catalogue/{number}.jpg?unique={stamp}" for number in range(1, len(pages) + 1)]
        return request.render("ocd_live_shop.vendor_catalogue", common.page_values(
            False,
            space_page="products",
            back="/ocd/espace/moi/produits",
            back_label=env._("Back to my products"),
            header_title=env._("My products"),
            vendor=vendor,
            images=images,
            count=len(products),
            boutique_url=request.httprequest.url_root.rstrip("/") + f"/ocd/boutique/{vendor.id}",
        ))

    @http.route("/ocd/espace/moi/catalogue/<int:number>.jpg", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def catalogue_image(self, number, unique=None, **kwargs):
        """A page of the catalogue (the products on sale, 4 per image by default), private to the
        vendor while they choose to share it."""
        vendor = common.current_vendor()
        if not vendor:
            raise request.not_found()
        products, stamp, pages = self._catalogue(vendor)
        if not 1 <= number <= len(pages):
            raise request.not_found()
        env = request.env
        url = request.httprequest.url_root.rstrip("/") + f"/ocd/boutique/{vendor.id}"
        lang = env.lang or ""
        data = drawn(("catalogue", vendor.id, number, stamp, lang, url), lambda: share_image.catalogue({
            "title": vendor.name,
            "subtitle": (env._("1 product") if len(products) == 1 else env._("%s products", len(products)))
            + (f" · {number}/{len(pages)}" if len(pages) > 1 else ""),
            "items": [
                {"photo": photo_bytes(p, "image_512"), "name": p.name, "price": common.money(p.list_price, p.currency_id)}
                for p in pages[number - 1]
            ],
            "cta": env._("Order on OCD Live"),
            "link": short_link(url),
            "url": url,
        }))
        response = jpeg_response(data, unique, stamp)
        response.headers["Cache-Control"] = response.headers["Cache-Control"].replace("public", "private")
        return response

    # === THE PRICE LABELS TO PRINT (M.7 of the plan) === #

    @http.route("/ocd/espace/moi/etiquettes", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def labels(self, produit=None, copies=None, **kwargs):
        """A sheet of price labels for the store: the name, the price as on the site and the QR
        code of each product on sale (all, or the ones of `produit`: "12" or "12,15"). The QR
        codes are in the page: nothing left to load when the phone prints it."""
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        products = env["product.template"]._ocd_vendor_products(vendor).filtered(
            lambda p: p.is_published and p.ocd_review_state == "approved"
        )
        chosen = {int(part) for part in (produit or "").split(",") if part.strip().isdigit()}
        if chosen:
            products = products.filtered(lambda p: p.id in chosen)
        copies = min(max(int(copies), 1), LABELS_MAX_COPIES) if str(copies or "").isdigit() else 1
        root = request.httprequest.url_root.rstrip("/")
        price_by_id = shop_common.prices(products)
        labels = []
        for product in products:
            price = price_by_id.get(product.id) or common.money(product.list_price, product.currency_id)
            labels.append({
                "name": product.name,
                "price": price,
                # A long price (« 125 000 FCFA ») is written smaller to hold beside the QR code
                "long": len(price) > LABEL_PRICE_SHORT,
                "qr": tools.qr_data_uri(root + product.website_url, box_size=4),
            })
        labels = [label for label in labels for _copy in range(copies)]
        return request.render("ocd_live_shop.vendor_labels", common.page_values(
            False,
            space_page="products",
            back="/ocd/espace/moi/produits",
            back_label=env._("Back to my products"),
            header_title=env._("My products"),
            vendor=vendor,
            labels=labels,
            chosen=",".join(str(product.id) for product in products) if chosen else "",
            copies=copies,
            max_copies=LABELS_MAX_COPIES,
        ))
