import re

from odoo import models
from odoo.tools import html2plaintext

from odoo.addons.whatsapp_cloud.tools import simplify

# « Where are you? »: the words of a customer who asks where a store is (without accents,
# case nor punctuation, see whatsapp_cloud.tools.simplify)
WHERE_WORDS = (
    "ou etes vous", "vous etes ou", "ou es tu", "tu es ou", "ou se trouve", "ou est le magasin",
    "le magasin est ou", "ou est la boutique", "la boutique est ou", "ou est votre magasin", "votre adresse",
    "ton adresse", "adresse du magasin", "adresse de la boutique", "localisation", "itineraire",
    "where are you", "where is the store", "where is your store", "where is the shop", "your address",
    "address of the store", "location of the store",
)
# A product or a boutique of OCD Live in a message: /shop/robe-en-wax-57, /ocd/boutique/12
PRODUCT_LINK = re.compile(r"/shop/[\w-]*?-(\d+)\b")
BOUTIQUE_LINK = re.compile(r"/ocd/boutique/(\d+)\b")
MAX_STORES = 5
RECENT_MESSAGES = 10


class DiscussChannel(models.Model):
    """The bot of OCD Live gives the stores of a vendor (chantier 20, A.2 of the plan of « My
    products », design VacancesProximite): « Where are you? » gets the stores of the vendor of the
    product the customer talks about (a link of the shop or of a boutique in the conversation),
    else of their latest order: the address, open or closed, the hours, the position to open in
    the maps. The button WhatsApp of a boutique goes to the number of the vendor: the bot does
    not see these conversations."""

    _inherit = "discuss.channel"

    def _ocd_asks_where(self, text):
        words = simplify(text)
        return any(phrase in words for phrase in WHERE_WORDS)

    def _ocd_vendors_in_question(self, text=""):
        """The vendors the customer talks about: of a product or a boutique linked in this
        message or in their last messages, else of their latest order."""
        self.ensure_one()
        env = self.env
        Partner = env["res.partner"].sudo()
        texts = [text or ""]
        customer = self.whatsapp_partner_id
        if customer:
            messages = self.message_ids.filtered(
                lambda message: message.message_type == "whatsapp_message" and message.author_id == customer
            ).sorted("id", reverse=True)[:RECENT_MESSAGES]
            texts += [html2plaintext(message.body or "") for message in messages]
        found = []
        for body in texts:
            for product_id in PRODUCT_LINK.findall(body):
                vendor = env["product.template"].sudo().browse(int(product_id)).exists().ocd_vendor_id
                if vendor:
                    found.append(vendor.id)
            for vendor_id in BOUTIQUE_LINK.findall(body):
                vendor = Partner.browse(int(vendor_id)).exists()
                if vendor.ocd_is_vendor:
                    found.append(vendor.id)
            if found:
                break
        if not found:
            for order in self._whatsapp_get_orders(limit=5):
                vendors = order.order_line.product_id.product_tmpl_id.sudo().ocd_vendor_id
                if vendors:
                    found = vendors.ids
                    break
        return Partner.browse(list(dict.fromkeys(found))).filtered(
            lambda vendor: vendor.ocd_is_vendor and vendor.ocd_vendor_state == "approved"
        )

    def _whatsapp_bot_answer(self, wa_message, content):
        """Override of `whatsapp_cloud_sale`: « Where are you? »."""
        if self._ocd_asks_where(wa_message.body or ""):
            vendors = self._ocd_vendors_in_question(wa_message.body or "")
            if vendors:
                self._ocd_send_vendor_stores(vendors)
                return True
        return super()._whatsapp_bot_answer(wa_message, content)

    def _whatsapp_send_stores(self):
        """Override of `whatsapp_cloud_sale`: the option « Our stores » gives the stores of the
        vendor in question, else the ones of OCD Live."""
        self.ensure_one()
        vendors = self._ocd_vendors_in_question()
        if vendors:
            return self._ocd_send_vendor_stores(vendors)
        return super()._whatsapp_send_stores()

    def _ocd_send_vendor_stores(self, vendors):
        """The stores of `vendors` the customers see, then their positions."""
        self.ensure_one()
        channel = self._whatsapp_customer_env()
        env = channel.env
        Place = env["ocd.vendor.place"]
        shown = Place._ocd_shown_by_vendor(vendors)
        blocks, pins = [], []
        for vendor in vendors:
            places = shown.get(vendor.id, Place).with_context(env.context)
            stores = places.filtered(lambda place: place.kind == "store")[:MAX_STORES]
            if not stores:
                area = places[:1]._ocd_area() if places else ", ".join(
                    part for part in (vendor.district_id.name, vendor.city) if part)
                blocks.append(env._(
                    "%(vendor)s has no store open to the public%(area)s: order on OCD Live, the products are delivered.",
                    vendor=vendor.name, area=env._(" (they sell from %s)", area) if area else "",
                ))
                continue
            lines = [env._("The stores of %s:", vendor.name)]
            for store in stores:
                entry = [f"*{store.name}*", store._ocd_address_line(), store._ocd_open_state()["label"]]
                entry += [f"🕘 {line}" for line in store._ocd_hours_lines()]
                if store._ocd_phone():
                    entry.append(f"📞 {store._ocd_phone()}")
                lines.append("\n".join(filter(None, entry)))
                if store._ocd_has_position():
                    pins.append(store)
            if vendor._ocd_on_holiday():
                lines.append(env._("%(vendor)s is on holiday until %(day)s: the orders start again that day.",
                                   vendor=vendor.name, day=vendor._ocd_holiday_back_text()))
            blocks.append("\n\n".join(lines))
        channel._whatsapp_send_bot_text("\n\n".join(blocks))
        for store in pins[:MAX_STORES]:
            channel._whatsapp_send_location(store.latitude, store.longitude, store.name, store._ocd_address_line())
        channel._whatsapp_send_follow_up()
        return True
