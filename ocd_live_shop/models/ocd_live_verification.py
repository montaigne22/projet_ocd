from odoo import api, models
from odoo.exceptions import UserError


class OcdLiveVerification(models.AbstractModel):
    """The new products of the vendors on the board of the checks, and the sale mode chosen
    when a new vendor is validated."""

    _inherit = "ocd.live.verification"

    @api.model
    def _ocd_columns(self):
        columns = super()._ocd_columns()
        columns.insert(1, {
            "key": "product",
            "label": self.env._("New products"),
            "empty": self.env._("No product waiting."),
            "items": self._ocd_product_items(),
        })
        return columns

    @api.model
    def _ocd_product_items(self):
        products = self.env["product.template"].search(
            [("ocd_vendor_id", "!=", False), ("ocd_review_state", "=", "to_check")], order="create_date"
        )
        reasons = self._ocd_reasons("product")
        modes = dict(self.env["res.partner"]._fields["ocd_delivery_mode"]._description_selection(self.env))
        items = []
        for product in products:
            vendor = product.ocd_vendor_id
            price = self.env["ocd.live.dashboard"]._ocd_money(product.list_price, product.currency_id)
            parts = [vendor.name, vendor.country_id.name]
            if product.is_storable:
                parts.append(self.env._("%s in stock", int(product.qty_available)))
            if vendor.ocd_sale_mode == "ocd":
                detail = self.env._("Sold by OCD · %s", (modes.get(vendor.ocd_delivery_mode) or "").lower())
            else:
                detail = self.env._("Direct contact: the customers write to %s.", vendor.name)
            items.append({
                "key": f"product_{product.id}",
                "kind": "product",
                "id": product.id,
                "title": f"{product.name} · {price}",
                "sub": " · ".join(part for part in parts if part),
                "detail": detail,
                "photo": f"/web/image/product.template/{product.id}/image_256" if product.image_128 else "",
                "open_label": self.env._("See it big"),
                "open_url": f"/web/image/product.template/{product.id}/image_1024",
                "ok_label": self.env._("Put online"),
                "reasons": reasons,
            })
        return items

    @api.model
    def _ocd_vendor_choices(self, vendor):
        choices = super()._ocd_vendor_choices(vendor)
        modes = vendor._fields["ocd_sale_mode"]._description_selection(self.env)
        choices.append({
            "name": "ocd_sale_mode",
            "label": self.env._("Sale mode to start"),
            "value": vendor.ocd_sale_mode or "direct",
            "options": [{"value": value, "label": label} for value, label in modes],
        })
        return choices

    @api.model
    def _ocd_history_rows(self, since):
        rows = super()._ocd_history_rows(since)
        for product in self.env["product.template"].search(
            [("ocd_vendor_id", "!=", False), ("ocd_review_date", ">=", since)]
        ):
            approved = product.ocd_review_state == "approved"
            rows.append(self._ocd_history_row(
                product.ocd_review_date,
                product.name,
                self.env._("Product put online") if approved else self.env._("Product refused"),
                approved,
            ))
        return rows

    @api.model
    def _ocd_models(self):
        return {**super()._ocd_models(), "product": "product.template"}

    @api.model
    def ocd_approve(self, kind, record_id, values=None):
        if kind != "product":
            return super().ocd_approve(kind, record_id, values)
        product = self._ocd_record(kind, record_id)
        product.action_ocd_approve()
        product.is_published = True
        return True

    @api.model
    def ocd_refuse(self, kind, record_id, reason_id):
        if kind != "product":
            return super().ocd_refuse(kind, record_id, reason_id)
        product = self._ocd_record(kind, record_id)
        reason = self.env["ocd.listing.refuse.reason"].browse(reason_id).exists()
        if not reason:
            raise UserError(self.env._("Choose the reason sent to the vendor."))
        product.action_ocd_refuse(reason)
        return True
