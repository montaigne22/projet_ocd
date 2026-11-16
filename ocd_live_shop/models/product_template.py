import re
from urllib.parse import quote as url_quote

from odoo import api, fields, models
from odoo.exceptions import UserError


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
    ocd_moment_ids = fields.One2many(
        comodel_name="ocd.live.moment", inverse_name="product_tmpl_id", string="Live Moments"
    )
    ocd_wa_clicks = fields.Integer(
        string="WhatsApp Contacts",
        copy=False,
        readonly=True,
        help="Number of visitors who wrote to the vendor on WhatsApp from the boutique.",
    )

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
        images = self.product_template_image_ids.filtered("image_128").sorted("sequence")
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
