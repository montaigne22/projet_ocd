"""The reviews of the buyers (chantier 2 of the roadmap, design GarantieAvis).

Only a buyer whose parcel was delivered gives a review: one per parcel (so one per vendor of the
order), stars and a word if they want, that they can change. The rating of WhatsApp (« Rate from 1
to 5 ») counts too. Their first name and the initial of their name are shown, never their number.
The note of a vendor shows from 3 reviews; before, « New vendor ». A review is online at once; the
vendor may report it, the team may hide it."""
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang

# The reviews from which the note of a vendor shows
MIN_REVIEWS = 3
COMMENT_MAX = 500


class OcdVendorReview(models.Model):
    _name = "ocd.vendor.review"
    _description = "Review Of A Buyer"
    _order = "create_date desc, id desc"
    _check_company_auto = True

    picking_id = fields.Many2one(
        comodel_name="stock.picking", string="Parcel", required=True, index=True, ondelete="cascade",
    )
    order_id = fields.Many2one(related="picking_id.sale_id", string="Order", store=True, index=True)
    vendor_id = fields.Many2one(
        comodel_name="res.partner", string="Vendor", required=True, index=True, ondelete="cascade",
    )
    partner_id = fields.Many2one(comodel_name="res.partner", string="Buyer", required=True, ondelete="cascade")
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    stars = fields.Integer(required=True, help="From 1 to 5.")
    comment = fields.Text(string="Word Of The Buyer")
    product_ids = fields.Many2many(
        comodel_name="product.template", relation="ocd_vendor_review_product_rel", column1="review_id",
        column2="product_id", string="Products",
    )
    source = fields.Selection(
        selection=[("tracking", "Page of the order"), ("whatsapp", "WhatsApp")], default="tracking", required=True,
    )
    state = fields.Selection(
        selection=[("published", "Shown"), ("reported", "Reported by the vendor"), ("hidden", "Hidden by the team")],
        default="published", required=True, index=True,
    )
    report_note = fields.Char(string="Why The Vendor Reports It", readonly=True)
    author_name = fields.Char(string="Shown As", compute="_compute_author_name")

    _unique_parcel = models.UniqueIndex("(picking_id)", "A parcel has one review.")

    @api.constrains("stars")
    def _check_stars(self):
        for review in self:
            if not 1 <= review.stars <= 5:
                raise ValidationError(self.env._("From 1 to 5 stars."))

    @api.depends("partner_id.name")
    def _compute_author_name(self):
        for review in self:
            review.author_name = review._ocd_author(review.partner_id.name)

    @api.model
    def _ocd_author(self, name):
        """« Estelle N. »: the first name and the initial of the name; a buyer known by their number
        only stays « A buyer »."""
        words = (name or "").split()
        if not words or words[0].startswith("+") or words[0][:1].isdigit():
            return self.env._("A buyer")
        return f"{words[0]} {words[-1][0].upper()}." if len(words) > 1 else words[0]

    @api.depends("vendor_id", "stars")
    def _compute_display_name(self):
        for review in self:
            review.display_name = f"{review.vendor_id.name} · {'★' * review.stars}"

    # === GIVE A REVIEW === #

    @api.model
    def _ocd_give(self, parcel, stars, comment=None, source="tracking"):
        """The buyer of `parcel` gives (or changes) their review of its vendor: only once the
        parcel is delivered. A rating of WhatsApp keeps the word written before."""
        parcel = parcel.sudo()
        try:
            stars = int(stars)
        except (TypeError, ValueError):
            stars = 0
        if not 1 <= stars <= 5:
            raise UserError(self.env._("Choose from 1 to 5 stars."))
        if not parcel.ocd_is_parcel or not parcel.ocd_vendor_id or parcel.ocd_stage != "delivered":
            raise UserError(self.env._("A review is given once the parcel is delivered."))
        comment = " ".join((comment or "").split())[:COMMENT_MAX]
        values = {"stars": stars, "source": source}
        if comment or source == "tracking":
            values["comment"] = comment or False
        review = self.sudo().search([("picking_id", "=", parcel.id)], limit=1)
        if review:
            if review.state == "hidden" and values.get("comment"):
                values["state"] = "published"
            review.write(values)
            return review
        return self.sudo().create({
            **values,
            "picking_id": parcel.id,
            "vendor_id": parcel.ocd_vendor_id.id,
            "partner_id": (parcel.sale_id.partner_id or parcel.partner_id).id,
            "company_id": parcel.company_id.id,
            "product_ids": [fields.Command.set(parcel.move_ids.product_id.product_tmpl_id.ids)],
        })

    # === WHAT IS SHOWN === #

    @api.model
    def _ocd_visible_domain(self):
        return [("state", "!=", "hidden")]

    @api.model
    def _ocd_stats(self, vendor_ids):
        """{vendor id: (average, count)} of the reviews shown."""
        groups = self.sudo()._read_group(
            [("vendor_id", "in", list(vendor_ids))] + self._ocd_visible_domain(),
            ["vendor_id"], ["stars:avg", "__count"],
        )
        return {vendor.id: (average or 0.0, count) for vendor, average, count in groups}

    @api.model
    def _ocd_note(self, average):
        """« 4,8 » in the language of the page."""
        return formatLang(self.env, average, digits=1)

    @api.model
    def _ocd_summary(self, vendor):
        """What the pages show of the reviews of `vendor`: {"count", "note" (False before 3
        reviews), "line" (« 4,8 · 37 reviews » or « New vendor »), "short" (« 4,8 (37) » or "")}."""
        average, count = self._ocd_stats([vendor.id]).get(vendor.id, (0.0, 0))
        env = self.env
        if count >= MIN_REVIEWS:
            note = self._ocd_note(average)
            reviews = env._("1 review") if count == 1 else env._("%s reviews", count)
            return {"count": count, "note": note, "line": f"{note} · {reviews}", "short": f"{note} ({count})"}
        return {"count": count, "note": False, "line": env._("New vendor"), "short": ""}

    @api.model
    def _ocd_card_line(self, vendor_id):
        """« 4,8 (37) » for a card of the lives (empty before 3 reviews)."""
        vendor = self.env["res.partner"].sudo().browse(int(vendor_id or 0)).exists()
        return self._ocd_summary(vendor)["short"] if vendor else ""

    @api.model
    def _ocd_latest(self, vendor, limit=3):
        """The last reviews shown of `vendor`, the ones with a word first."""
        reviews = self.sudo().search([("vendor_id", "=", vendor.id)] + self._ocd_visible_domain(), limit=50)
        return reviews.sorted(lambda review: (not review.comment, -review.id))[:limit]

    @api.model
    def _ocd_product_stats(self, products):
        """{product id: (average, count)} of the reviews shown that name these products."""
        stats = {}
        reviews = self.sudo().search([("product_ids", "in", products.ids)] + self._ocd_visible_domain())
        for product in products:
            stars = [review.stars for review in reviews if product in review.product_ids]
            if stars:
                stats[product.id] = (sum(stars) / len(stars), len(stars))
        return stats

    def _ocd_when(self):
        """« 3 days ago », « 2 weeks ago »."""
        self.ensure_one()
        days = (fields.Datetime.now() - self.create_date).days
        env = self.env
        if days < 1:
            return env._("today")
        if days < 7:
            return env._("1 day ago") if days == 1 else env._("%s days ago", days)
        if days < 31:
            return env._("1 week ago") if days < 14 else env._("%s weeks ago", days // 7)
        return env._("1 month ago") if days < 60 else env._("%s months ago", days // 30)

    # === THE VENDOR REPORTS, THE TEAM DECIDES === #

    def _ocd_report(self, note):
        """The vendor reports a review to the team: it stays shown until the team decides."""
        note = " ".join((note or "").split())[:200]
        if not note:
            raise UserError(self.env._("Say why the review is wrong."))
        for review in self.sudo():
            if review.state == "published":
                review.write({"state": "reported", "report_note": note})

    def action_ocd_hide(self):
        self.sudo().write({"state": "hidden"})

    def action_ocd_publish(self):
        self.sudo().write({"state": "published", "report_note": False})


class ResPartner(models.Model):
    _inherit = "res.partner"

    ocd_review_count = fields.Integer(string="Reviews", compute="_compute_ocd_review_count")

    def _compute_ocd_review_count(self):
        stats = self.env["ocd.vendor.review"]._ocd_stats(self.ids)
        for partner in self:
            partner.ocd_review_count = stats.get(partner._origin.id, (0, 0))[1]

    def action_ocd_view_reviews(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Reviews of %s", self.name),
            "res_model": "ocd.vendor.review",
            "view_mode": "list,form",
            "domain": [("vendor_id", "=", self.id)],
            "context": {"default_vendor_id": self.id},
        }


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _ocd_rate(self, stars):
        """The rating of the whole order (the page of before, WhatsApp): each parcel delivered gets
        it as the review of its vendor, the words written before kept."""
        super()._ocd_rate(stars)
        self._ocd_review_parcels(stars, "tracking")

    def _ocd_review_parcels(self, stars, source):
        for order in self:
            for parcel in order.sudo().picking_ids.filtered(
                lambda picking: picking.ocd_is_parcel and picking.ocd_vendor_id and picking.ocd_stage == "delivered"
            ):
                existing = self.env["ocd.vendor.review"].sudo().search([("picking_id", "=", parcel.id)], limit=1)
                self.env["ocd.vendor.review"]._ocd_give(
                    parcel, stars, comment=existing.comment if existing else None, source=source,
                )
