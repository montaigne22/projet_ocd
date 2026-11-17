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
            "label": self.env._("New products and changes"),
            "empty": self.env._("No product waiting."),
            "items": self._ocd_product_items() + self._ocd_change_items(),
        })
        columns.insert(2, {
            "key": "store",
            "label": self.env._("New stores"),
            "empty": self.env._("No store waiting."),
            "items": self._ocd_store_items(),
        })
        return columns

    @api.model
    def _ocd_store_items(self):
        """The stores the vendors added or moved (BoVerificationMagasins): the front, where, the
        hours, the position taken on the spot to open on the map."""
        _ = self.env._
        places = self.env["ocd.vendor.place"].search([("state", "=", "to_check")], order="create_date")
        reasons = self._ocd_reasons("store")
        modes = {"ocd": _("sold by OCD"), "direct": _("direct contact")}
        items = []
        for place in places:
            vendor = place.vendor_id
            facts = [place._ocd_address_line(), "; ".join(place._ocd_hours_lines()), place._ocd_phone()]
            detail = " · ".join(fact for fact in facts if fact)
            if place.previous_refusal:
                detail = _("Sent again after a refusal: %(reason)s. %(detail)s", reason=place.previous_refusal, detail=detail)
            if place._ocd_has_position():
                proof = _("Position taken on the spot, within %s m", place.position_accuracy or "?")
                open_label = _("See on the map")
                open_url = f"https://www.google.com/maps/search/?api=1&query={place.latitude:.6f},{place.longitude:.6f}"
            else:
                proof = _("No position")
                open_label = _("See it big") if place.photo else False
                open_url = f"/web/image/ocd.vendor.place/{place.id}/photo" if place.photo else False
            if not place.photo:
                proof = f"{proof} · {_('No photo of the front')}"
            items.append({
                "key": f"store_{place.id}",
                "kind": "store",
                "id": place.id,
                "title": place.name,
                "sub": " · ".join(part for part in (vendor.name, vendor.country_id.name, modes.get(vendor.ocd_sale_mode)) if part),
                "detail": f"{detail} · {proof}" if detail else proof,
                "photo": f"/web/image/ocd.vendor.place/{place.id}/photo/256x256" if place.photo else "",
                "open_label": open_label,
                "open_url": open_url,
                "ok_label": _("Put online"),
                "reasons": reasons,
            })
        return items

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
            if product.ocd_previous_refusal:
                # Corrected by the vendor: check what was refused
                detail = self.env._("Sent again after a refusal: %(reason)s. %(detail)s",
                                    reason=product.ocd_previous_refusal, detail=detail)
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
    def _ocd_change_items(self):
        """The changes of products on sale (2.1 of the plan, design GererProduits): before
        (still on sale) and now, side by side; accepted, the change shows at once."""
        _ = self.env._
        products = self.env["product.template"].search(
            [("ocd_vendor_id", "!=", False), ("ocd_change_state", "=", "to_check")], order="ocd_change_date"
        )
        reasons = self._ocd_reasons("product")
        items = []
        for product in products:
            items.append({
                "key": f"product_change_{product.id}",
                "kind": "product_change",
                "id": product.id,
                "tag": _("Change"),
                "title": product.name,
                "sub": " · ".join(part for part in (
                    product.ocd_vendor_id.name,
                    _("on sale during the check"),
                    _("sent %s", self._ocd_ago(product.ocd_change_date)),
                ) if part),
                "changes": product._ocd_change_rows(),
                "photo": f"/web/image/product.template/{product.id}/image_256" if product.image_128 else "",
                "open_label": _("Open the product"),
                "open_action": {
                    "type": "ir.actions.act_window", "res_model": "product.template", "res_id": product.id,
                    "views": [[False, "form"]], "target": "current",
                },
                "ok_label": _("Accept the change"),
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
        for product in self.env["product.template"].search([
            ("ocd_vendor_id", "!=", False), ("ocd_change_review_date", ">=", since),
            ("ocd_change_state", "in", ("approved", "refused")),
        ]):
            approved = product.ocd_change_state == "approved"
            rows.append(self._ocd_history_row(
                product.ocd_change_review_date,
                product.name,
                self.env._("Change put online") if approved else self.env._("Change refused"),
                approved,
            ))
        for place in self.env["ocd.vendor.place"].search([("kind", "=", "store"), ("review_date", ">=", since)]):
            approved = place.state == "approved"
            rows.append(self._ocd_history_row(
                place.review_date,
                place.name,
                self.env._("Store put online") if approved else self.env._("Store refused"),
                approved,
            ))
        return rows

    @api.model
    def _ocd_models(self):
        return {**super()._ocd_models(), "product": "product.template", "product_change": "product.template",
                "store": "ocd.vendor.place"}

    @api.model
    def ocd_approve(self, kind, record_id, values=None):
        if kind == "product_change":
            return self._ocd_record(kind, record_id).action_ocd_approve_change()
        if kind == "store":
            return self._ocd_record(kind, record_id).action_ocd_approve()
        if kind != "product":
            return super().ocd_approve(kind, record_id, values)
        product = self._ocd_record(kind, record_id)
        product.action_ocd_approve()
        product.is_published = True
        return True

    @api.model
    def ocd_refuse(self, kind, record_id, reason_id):
        if kind == "product_change":
            reason = self.env["ocd.listing.refuse.reason"].browse(reason_id).exists()
            if not reason:
                raise UserError(self.env._("Choose the reason sent to the vendor."))
            return self._ocd_record(kind, record_id).action_ocd_refuse_change(reason)
        if kind == "store":
            reason = self.env["ocd.listing.refuse.reason"].browse(reason_id).exists()
            if not reason:
                raise UserError(self.env._("Choose the reason sent to the vendor."))
            return self._ocd_record(kind, record_id).action_ocd_refuse(reason)
        if kind != "product":
            return super().ocd_refuse(kind, record_id, reason_id)
        product = self._ocd_record(kind, record_id)
        reason = self.env["ocd.listing.refuse.reason"].browse(reason_id).exists()
        if not reason:
            raise UserError(self.env._("Choose the reason sent to the vendor."))
        product.action_ocd_refuse(reason)
        return True
