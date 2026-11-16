from odoo import models


def first_of_each(records, key):
    """The first record of each `key` in `records`, in their order."""
    seen, kept = set(), []
    for record in records:
        if key(record) not in seen:
            seen.add(key(record))
            kept.append(record.id)
    return records.browse(kept)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _ocd_tell_vendor_review(self):
        """Override of `ocd_live_shop`: the vendor learns on WhatsApp that the team accepted
        their product, or refused it with its reason. One message per vendor and per answer when
        the team checks several products at once."""
        super()._ocd_tell_vendor_review()
        templates = {
            "approved": "ocd_live_shop_whatsapp.template_product_accepted",
            "refused": "ocd_live_shop_whatsapp.template_product_refused",
        }
        products = first_of_each(
            self.filtered(lambda p: p.ocd_vendor_id and p.ocd_review_state in templates),
            lambda p: (p.ocd_vendor_id.id, p.ocd_review_state),
        )
        Partner = self.env["res.partner"]
        return any([Partner._ocd_whatsapp_send(templates[p.ocd_review_state], p) for p in products])


class OcdVendorPlace(models.Model):
    _inherit = "ocd.vendor.place"

    def _ocd_tell_vendor_review(self):
        """Override of `ocd_live_shop`: the vendor learns on WhatsApp that the team checked their
        store (shown in their boutique), or refused it with its reason. A home is shown without
        a check: nothing to tell."""
        super()._ocd_tell_vendor_review()
        templates = {
            "approved": "ocd_live_shop_whatsapp.template_store_accepted",
            "refused": "ocd_live_shop_whatsapp.template_store_refused",
        }
        places = first_of_each(
            self.filtered(lambda p: p.kind == "store" and p.state in templates),
            lambda p: (p.vendor_id.id, p.state),
        )
        Partner = self.env["res.partner"]
        return any([Partner._ocd_whatsapp_send(templates[p.state], p) for p in places])
