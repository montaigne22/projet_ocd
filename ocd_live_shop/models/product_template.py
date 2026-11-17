import re
from urllib.parse import quote as url_quote

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import BinaryBytes


def _binary(data, filename):
    """The bytes of a photo sent by the vendor, with its name."""
    return BinaryBytes(data, filename=filename) if filename else data


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ocd_vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="OCD Vendor",
        index="btree_not_null",
        domain=[("ocd_is_vendor", "=", True)],
        tracking=True,
    )
    ocd_sale_mode = fields.Selection(related="ocd_vendor_id.ocd_sale_mode", string="Sale Mode")
    ocd_category_id = fields.Many2one(
        related="ocd_vendor_id.ocd_category_id",
        store=True,
        index="btree_not_null",
        string="Category Of The Vendor",
        help="Used by the shop to filter the products by category of the vendors.",
    )
    ocd_review_state = fields.Selection(
        selection=[("to_check", "To check"), ("approved", "Approved"), ("refused", "Refused")],
        string="Review",
        default="approved",
        tracking=True,
        help="The products added by the vendors from their space are checked by the team "
        "before they appear on the website.",
    )
    ocd_review_date = fields.Datetime(string="Checked At", copy=False, readonly=True)
    ocd_refuse_reason_id = fields.Many2one(
        comodel_name="ocd.listing.refuse.reason",
        string="Reason Of The Refusal",
        copy=False,
        tracking=True,
        domain=[("applies_to", "=", "product")],
        help="Shown to the vendor in « My products », with its message: they correct the product and "
        "send it again.",
    )
    ocd_previous_refusal = fields.Char(
        string="Sent Again After",
        copy=False,
        readonly=True,
        help="The reason of the last refusal of a product the vendor corrected and sent again.",
    )
    ocd_form_token = fields.Char(
        string="Form Of The Vendor",
        copy=False,
        readonly=True,
        help="The form of « My products » that added the product: sent twice (a second tap on a "
        "slow network), it adds one product only.",
    )

    _ocd_form_token_uniq = models.Constraint(
        "unique(ocd_vendor_id, ocd_form_token)",
        "This product was already added from this form.",
    )
    ocd_vendor_retired = fields.Boolean(
        string="Taken Off Sale By The Vendor",
        copy=False,
        tracking=True,
        help="The vendor took the product off sale from « My products »: not shown, never deleted "
        "(the past orders keep it), and the vendor can put it back on sale.",
    )
    # A change of a product on sale (2.1 of the plan): checked by the team while the version of
    # today stays on sale
    ocd_change_state = fields.Selection(
        selection=[("to_check", "To check"), ("approved", "Accepted"), ("refused", "Refused")],
        string="Change Of The Vendor",
        copy=False,
        tracking=True,
        index="btree_not_null",
        help="The vendor changed the name (or the photos) of a product on sale: the team checks it while "
        "the product stays on sale as it was.",
    )
    ocd_change_name = fields.Char(string="New Name To Check", copy=False, tracking=True)
    ocd_change_date = fields.Datetime(string="Change Sent At", copy=False, readonly=True)
    ocd_change_review_date = fields.Datetime(string="Change Checked At", copy=False, readonly=True)
    ocd_change_reason_id = fields.Many2one(
        comodel_name="ocd.listing.refuse.reason",
        string="Reason Of The Refusal Of The Change",
        copy=False,
        tracking=True,
        domain=[("applies_to", "=", "product")],
        help="Shown to the vendor in « My products »: the product stays on sale as it was, the vendor "
        "corrects the change and sends it again.",
    )
    ocd_price_ids = fields.One2many(
        comodel_name="ocd.product.price", inverse_name="product_tmpl_id", string="Prices", readonly=True
    )
    ocd_moment_ids = fields.One2many(
        comodel_name="ocd.live.moment", inverse_name="product_tmpl_id", string="Live Moments"
    )
    ocd_wa_clicks = fields.Integer(
        string="WhatsApp Contacts",
        copy=False,
        readonly=True,
        help="Number of visitors who wrote to the vendor on WhatsApp from the boutique.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        products.filtered("ocd_vendor_id")._ocd_log_prices({}, source="creation")
        return products

    def write(self, vals):
        if "list_price" not in vals:
            return super().write(vals)
        before = {product.id: product.list_price for product in self}
        result = super().write(vals)
        self.filtered("ocd_vendor_id")._ocd_log_prices(before)
        return result

    def _ocd_log_prices(self, before, source=None):
        """A line in the history of the prices of each product whose price changed (`before`:
        {product id: price before}). Its author: `source`, else the context of the change (the
        vendor from their space), else the team."""
        context = self.env.context
        source = source or context.get("ocd_price_source") or "team"
        lines = []
        for product in self:
            previous = before.get(product.id, 0.0)
            if product.id in before and product.currency_id.compare_amounts(previous, product.list_price) == 0:
                continue
            lines.append({
                "product_tmpl_id": product.id,
                "price": product.list_price,
                "previous_price": previous,
                "gap": self.env["ocd.product.price"]._ocd_gap(previous, product.list_price),
                "source": source,
                "confirmed": bool(context.get("ocd_price_confirmed")),
            })
        if lines:
            self.env["ocd.product.price"].sudo().create(lines)

    def _ocd_price_needs_confirm(self, price):
        """Whether the vendor confirms the new `price`: a change bigger than the setting (50 %
        by default) of a price the product had."""
        self.ensure_one()
        limit = (self.company_id or self.env.company).ocd_price_gap_confirm
        gap = self.env["ocd.product.price"]._ocd_gap(self.list_price, price)
        return bool(limit) and abs(gap) > limit

    @api.constrains("is_published", "ocd_review_state")
    def _check_ocd_review_before_publication(self):
        for product in self:
            if product.is_published and product.ocd_vendor_id and product.ocd_review_state != "approved":
                raise UserError(
                    self.env._("The product %s must be approved before it is published.", product.name)
                )

    def action_ocd_approve(self):
        self.write({
            "ocd_review_state": "approved",
            "ocd_review_date": fields.Datetime.now(),
            "ocd_refuse_reason_id": False,
            "ocd_previous_refusal": False,
        })
        self._ocd_tell_vendor_review()
        return True

    def action_ocd_refuse(self, reason=None):
        """Refuse the products with `reason` (from the form: the reason chosen on it). The vendor
        sees its message in « My products », corrects the product and sends it again: a refusal
        always says why."""
        for product in self:
            why = reason or product.ocd_refuse_reason_id
            if not why:
                raise UserError(self.env._("Choose the reason sent to the vendor."))
            product.write({
                "ocd_review_state": "refused",
                "is_published": False,
                "ocd_review_date": fields.Datetime.now(),
                "ocd_refuse_reason_id": why.id,
                "ocd_previous_refusal": False,
            })
            product.message_post(body=self.env._("Product refused: %s", why.name))
        self._ocd_tell_vendor_review()
        return True

    def _ocd_tell_vendor_review(self):
        """Tell the vendors the answer of the team on their products (accepted, or refused with
        its reason): sent on WhatsApp by `ocd_live_shop_whatsapp`."""
        return False

    def _ocd_refusal_text(self):
        """What the vendor reads about the refusal of the product, or False."""
        self.ensure_one()
        if self.ocd_review_state != "refused":
            return False
        reason = self.ocd_refuse_reason_id
        return reason.message or reason.name or self.env._("Write to OCD Live to know why.")

    def _ocd_vendor_can_correct(self):
        """A product the vendor corrects from their space: refused, or still waiting for the
        check. (A product on sale is changed in another way: its new name or photo are checked
        while the old ones stay on sale.)"""
        self.ensure_one()
        return self.ocd_review_state in ("refused", "to_check")

    def _ocd_vendor_correct(self, values):
        """Write the corrections of the vendor (`values`: name, price, photo); a refused product
        goes back to the check of the team, which sees the reason of the refusal."""
        self.ensure_one()
        if not self._ocd_vendor_can_correct():
            raise UserError(self.env._("This product cannot be changed here."))
        if self.ocd_review_state == "refused":
            values = {
                **values,
                "ocd_review_state": "to_check",
                "ocd_previous_refusal": self.ocd_refuse_reason_id.name or self.env._("Refused"),
                "ocd_refuse_reason_id": False,
            }
            self.write(values)
            self.message_post(body=self.env._(
                "The vendor corrected the product and sent it again (refused for: %s).", self.ocd_previous_refusal,
            ))
        else:
            self.write(values)
        return True

    # === CHANGE A PRODUCT ON SALE (2.1 of the plan of « My products ») === #

    def _ocd_vendor_can_change(self):
        """A product the vendor changes while it stays on sale: checked by the team before."""
        self.ensure_one()
        return self.ocd_review_state == "approved"

    def _ocd_change_waiting(self):
        """What of the change of the vendor waits for the team (to check, or refused and not
        corrected yet): "name", "photos", "colours"."""
        self.ensure_one()
        parts = []
        if self.ocd_change_name and self.ocd_change_name != self.name:
            parts.append("name")
        if self._ocd_new_images():
            parts.append("photos")
        if self._ocd_new_colour_values():
            parts.append("colours")
        return parts

    def _ocd_new_images(self, states=("to_check", "refused")):
        self.ensure_one()
        return self.sudo().product_template_image_ids.filtered(lambda image: image.ocd_review_state in states)

    def _ocd_new_colour_values(self, states=("to_check", "refused")):
        self.ensure_one()
        return self.sudo().attribute_line_ids.product_template_value_ids.filtered(
            lambda value: value.ocd_image_state in states and value.ocd_image_pending
        )

    def _ocd_change_settle(self):
        """Nothing left of the change of the vendor (a new photo removed, the name of today
        typed again): no change to check any more."""
        for product in self.sudo():
            if product.ocd_change_state in ("to_check", "refused") and not product._ocd_change_waiting():
                product.write({"ocd_change_state": False, "ocd_change_reason_id": False, "ocd_change_name": False})

    def _ocd_change_rows(self):
        """The change of the vendor, before (on sale) and now, for the board of the checks:
        [{label, before, now, before_photos, now_photos}]."""
        self.ensure_one()
        _ = self.env._
        rows = []
        waiting = self._ocd_change_waiting()
        if "name" in waiting:
            rows.append({"label": _("Name"), "before": self.name, "now": self.ocd_change_name})
        if "photos" in waiting:
            photos = self._ocd_vendor_photos()
            shown = [photo for photo in photos if photo["state"] == "approved"]
            rows.append({
                "label": _("Photos"),
                "before_photos": [photo["bo"] for photo in shown],
                "now_photos": [{"src": photo["bo"], "new": photo["state"] == "to_check"}
                               for photo in photos if photo["state"] in ("approved", "to_check")],
            })
        for value in self._ocd_new_colour_values(("to_check",)):
            rows.append({
                "label": _("Colour %s", value.name),
                "before": "" if value.ocd_image else _("No photo"),
                "before_photos": [f"/web/image/product.template.attribute.value/{value.id}/ocd_image/256x256"]
                if value.ocd_image else [],
                "now_photos": [{"src": f"/web/image/product.template.attribute.value/{value.id}/ocd_image_pending/256x256",
                                "new": True}],
            })
        # The price changed with the change: already on sale, not checked
        price = self.ocd_price_ids.filtered(
            lambda line: line.source == "vendor" and self.ocd_change_date and line.create_date >= self.ocd_change_date
        )[:1]
        if price:
            money = self.env["ocd.live.dashboard"]._ocd_money
            rows.append({
                "label": _("Price"),
                "before": money(price.previous_price, self.currency_id),
                "now": _("%(price)s (already on sale, confirmed by the vendor)", price=money(price.price, self.currency_id))
                if price.confirmed else _("%s (already on sale)", money(price.price, self.currency_id)),
            })
        return rows

    def _ocd_vendor_change(self, name, price, confirmed=False):
        """The vendor changes a product on sale: the price at once (in the history of the
        prices), the name checked by the team while the product stays on sale as it was. Return
        whether something waits for the check."""
        self.ensure_one()
        if not self._ocd_vendor_can_change():
            raise UserError(self.env._("This product cannot be changed here."))
        product = self.sudo()
        if product.currency_id.compare_amounts(price, product.list_price):
            product.with_context(ocd_price_source="vendor", ocd_price_confirmed=confirmed).list_price = price
        if name != product.name:
            if name != product.ocd_change_name or product.ocd_change_state != "to_check":
                product.write({"ocd_change_name": name})
                product._ocd_change_sent()
        elif product.ocd_change_name:
            # Back to the name on sale: nothing left to check for the name
            product.ocd_change_name = False
            product._ocd_change_settle()
        if product.ocd_change_state == "refused" and product._ocd_change_waiting():
            # Saved again after a refusal: the photos kept go back to the check with the rest
            product._ocd_change_sent()
        return product.ocd_change_state == "to_check"

    def _ocd_change_sent(self):
        """Something new to check in the change of the vendor."""
        for product in self.sudo():
            refused = product.ocd_change_state == "refused" and product.ocd_change_reason_id.name
            product._ocd_new_images(("refused",)).ocd_review_state = "to_check"
            product._ocd_new_colour_values(("refused",)).ocd_image_state = "to_check"
            product.write({
                "ocd_change_state": "to_check",
                "ocd_change_date": self.env.cr.now(),
                "ocd_change_reason_id": False,
            })
            body = (self.env._("The vendor sent a change again (refused for: %s).", refused) if refused
                    else self.env._("The vendor sent a change to check."))
            product.message_post(body=body)

    def action_ocd_approve_change(self):
        """The team accepts the change of the vendor: it shows at once."""
        for product in self.filtered(lambda p: p.ocd_change_state == "to_check"):
            values = {
                "ocd_change_state": "approved",
                "ocd_change_review_date": fields.Datetime.now(),
                "ocd_change_reason_id": False,
                "ocd_change_name": False,
            }
            if product.ocd_change_name and product.ocd_change_name != product.name:
                values["name"] = product.ocd_change_name
            product._ocd_new_images(("to_check",)).ocd_review_state = "approved"
            for value in product._ocd_new_colour_values(("to_check",)):
                value.write({"ocd_image": value.ocd_image_pending, "ocd_image_pending": False, "ocd_image_state": False})
            product.write(values)
            product.message_post(body=self.env._("Change accepted."))
        self._ocd_tell_vendor_change()
        return True

    def action_ocd_refuse_change(self, reason=None):
        """The team refuses the change of the vendor, with its reason: the product stays on
        sale as it was; the vendor corrects the change and sends it again."""
        for product in self.filtered(lambda p: p.ocd_change_state == "to_check"):
            why = reason or product.ocd_change_reason_id
            if not why:
                raise UserError(self.env._("Choose the reason sent to the vendor."))
            product._ocd_new_images(("to_check",)).ocd_review_state = "refused"
            product._ocd_new_colour_values(("to_check",)).ocd_image_state = "refused"
            product.write({
                "ocd_change_state": "refused",
                "ocd_change_review_date": fields.Datetime.now(),
                "ocd_change_reason_id": why.id,
            })
            product.message_post(body=self.env._("Change refused: %s", why.name))
        self._ocd_tell_vendor_change()
        return True

    def _ocd_tell_vendor_change(self):
        """Tell the vendors the answer of the team on the change of their products: sent on
        WhatsApp by `ocd_live_shop_whatsapp`."""
        return False

    def _ocd_change_refusal_text(self):
        """What the vendor reads about the refusal of the change, or False."""
        self.ensure_one()
        if self.ocd_change_state != "refused":
            return False
        reason = self.ocd_change_reason_id
        return reason.message or reason.name or self.env._("Write to OCD Live to know why.")

    # === THE PHOTOS OF A PRODUCT (2.6 of the plan of « My products ») === #
    #
    # Odoo keeps the photos of a product in their order, the first one being the main photo (the
    # photo of the product, of the cards): moving a photo first makes it the main one. A new photo
    # of a product on sale is checked by the team: it never goes first before that.

    def _ocd_vendor_images(self):
        """The photos of the product in their order, the main one first."""
        self.ensure_one()
        return self.sudo().product_template_image_ids.filtered("image_128").sorted(lambda i: (i.sequence, i.id))

    def _ocd_vendor_photos(self):
        """The photos of the product for the vendor and the team, the main one first:
        [{key, image, state, main, bo}]. A product whose photo Odoo did not copy among its
        photos (made before) shows its main photo alone."""
        self.ensure_one()
        product = self.sudo()
        images = product._ocd_vendor_images()
        if not images:
            if not product.image_128:
                return []
            return [{
                "key": "principale", "image": False, "state": "approved", "main": True,
                "bo": f"/web/image/product.template/{product.id}/image_256",
            }]
        return [{
            "key": str(image.id), "image": image, "state": image.ocd_review_state, "main": index == 0,
            "bo": f"/web/image/product.image/{image.id}/image_256",
        } for index, image in enumerate(images)]

    def _ocd_photos_max(self):
        self.ensure_one()
        return max((self.company_id or self.env.company).ocd_product_photos_max or 8, 1)

    def _ocd_ensure_photo_images(self):
        """The main photo among the photos of the product, as Odoo keeps it (a product made
        before has it alone)."""
        self.ensure_one()
        product = self.sudo()
        if product.image_1920 and not product._ocd_vendor_images():
            product._set_extra_image_from_main_image(product.image_1920)

    def _ocd_vendor_add_photo(self, data, filename):
        """A photo the vendor adds, after the others: checked by the team before it shows, for
        a product on sale (it stays on sale as it was); a product not checked yet is checked
        with it."""
        self.ensure_one()
        product = self.sudo()
        if len(product._ocd_vendor_photos()) >= product._ocd_photos_max():
            raise UserError(self.env._("%s photos at most: remove one first.", product._ocd_photos_max()))
        product._ocd_ensure_photo_images()
        on_sale = product._ocd_vendor_can_change()
        last = max(product.product_template_image_ids.mapped("sequence") or [0])
        image = self.env["product.image"].sudo().with_context(skip_update_main_image=True).create({
            "name": product.name,
            "product_tmpl_id": product.id,
            "image_1920": _binary(data, filename),
            "sequence": last + 1,
            "ocd_review_state": "to_check" if on_sale else "approved",
        })
        if on_sale:
            product._ocd_change_sent()
        else:
            # A product without a photo yet takes this one as its main photo
            product._set_main_image_from_extra_images()
            product.message_post(body=self.env._("The vendor added a photo."))
        return image

    def _ocd_vendor_image(self, key):
        """The photo `key` of the product (the id of one of its photos, « principale » for the
        main one)."""
        self.ensure_one()
        product = self.sudo()
        if key == "principale":
            product._ocd_ensure_photo_images()
            return product._ocd_vendor_images()[:1]
        image = product.product_template_image_ids.filtered(lambda i: str(i.id) == str(key))
        if not image:
            raise UserError(self.env._("This photo is not one of the product."))
        return image

    def _ocd_vendor_remove_photo(self, key):
        """Remove a photo. The main one is replaced by the next checked photo: a product keeps
        one checked photo at least."""
        self.ensure_one()
        product = self.sudo()
        image = product._ocd_vendor_image(key)
        images = product._ocd_vendor_images()
        checked = images.filtered(lambda i: i.ocd_review_state == "approved")
        if image.ocd_review_state == "approved" and not (checked - image):
            raise UserError(self.env._("Add another photo before you remove this one: a product keeps one photo."))
        if image == images[:1]:
            # The next checked photo becomes the main one, never a photo not checked yet
            following = (checked - image)[:1]
            following.with_context(skip_update_main_image=True).sequence = image.sequence - 1
        image.unlink()
        product.message_post(body=self.env._("The vendor removed a photo."))
        product._ocd_change_settle()
        return True

    def _ocd_vendor_move_photo(self, key):
        """Move a checked photo one place earlier; first, it becomes the main photo (the photo
        of the cards)."""
        self.ensure_one()
        product = self.sudo()
        image = product._ocd_vendor_image(key)
        if image.ocd_review_state != "approved":
            return False
        images = product._ocd_vendor_images()
        index = images.ids.index(image.id)
        if index == 0:
            return False
        if len(set(images.mapped("sequence"))) < len(images):
            for position, other in enumerate(images):
                other.with_context(skip_update_main_image=True).sequence = position + 1
        previous = images[index - 1]
        mine, theirs = image.sequence, previous.sequence
        previous.with_context(skip_update_main_image=True).sequence = mine
        # Its sequence written last: Odoo makes the first photo the main one
        image.sequence = theirs
        return True

    def _ocd_vendor_colour_photo(self, value, data, filename):
        """The photo of the product in the colour `value`: for a product on sale, checked by the
        team while the photo of today (or none) stays."""
        self.ensure_one()
        product = self.sudo()
        if product._ocd_vendor_can_change():
            value.sudo().write({"ocd_image_pending": _binary(data, filename), "ocd_image_state": "to_check"})
            product._ocd_change_sent()
        else:
            value.sudo().ocd_image = _binary(data, filename)
        return True

    # === TAKE OFF SALE, PUT BACK (2.2 of the plan of « My products ») === #

    def _ocd_vendor_can_retire(self):
        """A product the vendor can take off sale: checked and shown by the team."""
        self.ensure_one()
        return self.ocd_review_state == "approved" and self.is_published and not self.ocd_vendor_retired

    def _ocd_vendor_retire(self):
        """The vendor takes the product off sale: no longer shown, never deleted (the past
        orders keep it). The customers waiting for it are told when it is back on sale."""
        for product in self:
            if not product._ocd_vendor_can_retire():
                raise UserError(self.env._("The product %s is not on sale.", product.name))
            product.sudo().write({"is_published": False, "ocd_vendor_retired": True})
            product.sudo().message_post(body=self.env._("Taken off sale by the vendor."))
        return True

    def _ocd_vendor_put_back(self):
        """The vendor puts back on sale a product they took off: shown again at once (it was
        checked before)."""
        for product in self:
            if not product.ocd_vendor_retired or product.ocd_review_state != "approved":
                raise UserError(self.env._("The product %s cannot be put back on sale.", product.name))
            product.sudo().write({"is_published": True, "ocd_vendor_retired": False})
            product.sudo().message_post(body=self.env._("Put back on sale by the vendor."))
        return True

    def action_ocd_show_on_live(self):
        """Show this product on the boutique of the vendor during the live of the context."""
        self.ensure_one()
        booking = self.env["ocd.live.booking"].browse(self.env.context.get("ocd_booking_id")).exists()
        if not booking:
            raise UserError(self.env._("Open the live first."))
        booking._ocd_show_product(self)
        return True

    # === PHOTOS OF THE PAGE === #

    @api.model
    def _ocd_photo_stamp(self, record):
        """A part of the address of the photos of `record` that changes with them: the browsers
        and the CDN keep an address with its version (?unique=) a year."""
        return record.write_date.strftime("%Y%m%d%H%M%S") if record.write_date else "0"

    def _ocd_image_url(self, size="image_512"):
        """The address of the photo of the product for the cards, with its version; empty when
        the product has no photo."""
        self.ensure_one()
        if not self.sudo().image_128:
            return False
        return f"/web/image/product.template/{self.id}/{size}?unique={self._ocd_photo_stamp(self)}"

    @api.model
    def _ocd_photo(self, record, field=None):
        """A photo for the page: shown (1024 px) and opened full screen (1920 px). The address
        changes with the photo, so that a new photo is never hidden by the cache."""
        stamp = self._ocd_photo_stamp(record)
        base = f"/web/image/{record._name}/{record.id}"
        if field:
            return {"src": f"{base}/{field}/1024x1024?unique={stamp}", "full": f"{base}/{field}?unique={stamp}"}
        return {"src": f"{base}/image_1024?unique={stamp}", "full": f"{base}/image_1920?unique={stamp}"}

    def _ocd_page_photos(self):
        """The main photo of the product (or None) and its other photos. Odoo keeps a copy of
        the main photo among the photos of the product: it is shown once."""
        self.ensure_one()
        main = self._ocd_photo(self) if self.image_128 else None
        # A new photo of a product on sale shows once the team checked it (chantier 19)
        images = self.product_template_image_ids.filtered(
            lambda image: image.image_128 and image.ocd_review_state == "approved"
        ).sorted("sequence")
        if not images:
            return main, []
        checksums = {
            (row["res_model"], row["res_id"]): row["checksum"]
            for row in self.env["ir.attachment"].sudo().search_read([
                "|",
                "&", ("res_model", "=", "product.template"), ("res_id", "=", self.id),
                "&", ("res_model", "=", "product.image"), ("res_id", "in", images.ids),
                ("res_field", "=", "image_1920"),
            ], ["res_model", "res_id", "checksum"])
        }
        main_checksum = checksums.get(("product.template", self.id))
        extras = [
            self._ocd_photo(image) for image in images
            if not main_checksum or checksums.get(("product.image", image.id)) != main_checksum
        ]
        return main, extras

    def _ocd_variant_photo(self, variant):
        """The photo of a variant: its own, else the one of its colour, else None (the main one)."""
        self.ensure_one()
        if variant.image_variant_128:
            return self._ocd_photo(variant)
        for value in variant.product_template_attribute_value_ids:
            if value.ocd_image:
                return self._ocd_photo(value, "ocd_image")
        return None

    def _ocd_last_moment(self):
        """The last moment this product was shown in a live whose replay is published."""
        self.ensure_one()
        return self.ocd_moment_ids.filtered(
            lambda moment: moment.booking_id.replay_published and moment.booking_id.replay_url
        ).sorted(lambda moment: (moment.booking_id.start_datetime, moment.offset_seconds))[-1:]

    def _ocd_whatsapp_url(self, values=None, link=None):
        """Return the WhatsApp link to the vendor, with a message about the product: the
        values chosen (colour, size...) and the link of the product, when given."""
        self.ensure_one()
        digits = re.sub(r"\D", "", self.ocd_vendor_id.phone or "")
        if len(digits) < 8:
            return False
        text = self.env._("Hello, I saw %(product)s on OCD Live.", product=self.name)
        if values:
            text = f"{text} {self.env._('My choice: %s.', ', '.join(values))}"
        if link:
            text = f"{text} {link}"
        return f"https://wa.me/{digits}?text={url_quote(text)}"

    # === THE BOUTIQUE OF THE VENDOR: ORDER AND COPIES === #

    @api.model
    def _ocd_vendor_products(self, vendor):
        """The products of `vendor` in the order of their boutique."""
        return self.sudo().search([("ocd_vendor_id", "=", vendor.id)], order="website_sequence, id")

    @api.model
    def _ocd_first_sequence(self, vendor):
        """The place of a product put first in the boutique of `vendor` (a new one, a copy), or
        None when the vendor has no product yet (the default place of Odoo)."""
        [[lowest]] = self.sudo()._read_group([("ocd_vendor_id", "=", vendor.id)], [], ["website_sequence:min"])
        return lowest - 1 if lowest is not None else None

    def _ocd_move_in_boutique(self, where):
        """Move a product in the boutique of its vendor: "first", "up" or "down" one place. The
        products of the other vendors keep their places, and one or two products only are
        written. Return whether it moved."""
        self.ensure_one()
        products = self._ocd_vendor_products(self.ocd_vendor_id)
        index = products.ids.index(self.id)
        if where == "first":
            if index == 0:
                return False
            self.sudo().website_sequence = products[0].website_sequence - 1
            return True
        other_index = {"up": index - 1, "down": index + 1}.get(where)
        if other_index is None or not 0 <= other_index < len(products):
            return False
        other = products[other_index]
        if other.website_sequence == self.website_sequence:
            # The same place number (products made elsewhere): make them distinct first
            last = None
            for product in products:
                if last is not None and product.website_sequence <= last:
                    product.website_sequence = last + 1
                last = product.website_sequence
        mine, theirs = self.website_sequence, other.website_sequence
        self.sudo().website_sequence = theirs
        other.website_sequence = mine
        return True

    def _ocd_vendor_duplicate(self):
        """A copy made by the vendor (the same model in another fabric): checked by the team like
        a new product, first in the boutique, without stock and without the history of the
        original (contacts, refusals)."""
        self.ensure_one()
        values = {
            "name": self.env._("%s (copy)", self.name),
            "ocd_review_state": "to_check",
            "is_published": False,
            "ocd_refuse_reason_id": False,
            "ocd_previous_refusal": False,
        }
        first = self._ocd_first_sequence(self.ocd_vendor_id)
        if first is not None:
            values["website_sequence"] = first
        copy = self.sudo().copy(values)
        copy.message_post(body=self.env._("Copy of %s, made by the vendor.", self.name))
        return copy

    def _ocd_free_total(self):
        """Pieces of the product free to sell, all its variants together (messages to the vendor)."""
        self.ensure_one()
        return sum(self.product_variant_ids._ocd_free_qties().values())

    def _ocd_vendor_products_path(self):
        """« My products » of the vendor of the product, opened by their personal link (the
        button of a WhatsApp message): without the domain, Meta adds it."""
        self.ensure_one()
        return f"ocd/espace/{self.ocd_vendor_id._ocd_get_space_token()}/produits"

    def _ocd_single_variant(self):
        """The variant of a product without variants, whose stock the vendor changes from their
        space (the stock of each variant is changed from the back office)."""
        self.ensure_one()
        if len(self.product_variant_ids) != 1:
            raise UserError(self.env._("Change the stock of the product %s from the back office.", self.name))
        return self.product_variant_ids

    def _ocd_set_stock(self, quantity):
        """Make `quantity` pieces of a product without variants free to sell (the pieces reserved
        for orders are kept), as an inventory adjustment traced in the stock moves."""
        return self._ocd_single_variant()._ocd_set_free_stock(quantity)

    def _ocd_change_stock(self, delta):
        """Add `delta` pieces to the free stock of a product without variants; return it."""
        return self._ocd_single_variant()._ocd_change_stock(delta)
