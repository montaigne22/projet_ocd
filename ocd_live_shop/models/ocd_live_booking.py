import re
from urllib.parse import parse_qs, urlparse

from odoo import api, fields, models
from odoo.exceptions import UserError


class OcdLiveBooking(models.Model):
    _inherit = "ocd.live.booking"

    current_product_tmpl_id = fields.Many2one(
        comodel_name="product.template", string="Shown Now", copy=False
    )
    moment_ids = fields.One2many(
        comodel_name="ocd.live.moment", inverse_name="booking_id", string="Moments Of The Replay"
    )
    ocd_visit_count = fields.Integer(
        string="Boutique Visits",
        copy=False,
        readonly=True,
        help="Visits of the boutique of the vendor during the live, one per browser.",
    )
    vendor_product_ids = fields.Many2many(
        comodel_name="product.template",
        string="Products Of The Vendor",
        compute="_compute_vendor_product_ids",
    )

    @api.depends("partner_id")
    def _compute_vendor_product_ids(self):
        products = self.env["product.template"].search([
            ("ocd_vendor_id", "in", self.partner_id.ids),
            ("sale_ok", "=", True),
            ("ocd_review_state", "=", "approved"),
        ])
        by_vendor = products.grouped("ocd_vendor_id")
        for booking in self:
            booking.vendor_product_ids = by_vendor.get(booking.partner_id, self.env["product.template"])

    def _ocd_show_product(self, product):
        """Show `product` on the boutique of the vendor and note the moment for the replay."""
        self.ensure_one()
        if self.state not in ("confirmed", "done"):
            raise UserError(self.env._("The live is not confirmed."))
        if product.ocd_vendor_id != self.partner_id:
            raise UserError(self.env._("This product does not belong to the vendor of the live."))
        offset = max(int((fields.Datetime.now() - self.start_datetime).total_seconds()), 0)
        self.current_product_tmpl_id = product
        self.env["ocd.live.moment"].create({
            "booking_id": self.id,
            "product_tmpl_id": product.id,
            "offset_seconds": offset,
        })

    def _ocd_count_visit(self):
        """Count a visit of the boutique during the live, in one query (many visitors at once)."""
        self.ensure_one()
        self.env.cr.execute(
            "UPDATE ocd_live_booking SET ocd_visit_count = COALESCE(ocd_visit_count, 0) + 1 WHERE id = %s",
            [self.id],
        )
        self.invalidate_recordset(["ocd_visit_count"])

    def _ocd_replay_embed(self):
        """How the page plays the replay: {platform, id, seek}. YouTube and TikTok (a published
        video) play in the page and go to a moment; Facebook plays in the page from a moment;
        Instagram and the other links open on their site (no moment)."""
        self.ensure_one()
        url = (self.replay_url or "").strip()
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        for prefix in ("www.", "m.", "mobile.", "music."):
            host = host.removeprefix(prefix)
        if host in ("youtube.com", "youtube-nocookie.com", "youtu.be"):
            video = ""
            if host == "youtu.be":
                video = parsed.path.strip("/").split("/")[0]
            elif parsed.path == "/watch":
                video = (parse_qs(parsed.query).get("v") or [""])[0]
            else:
                match = re.match(r"^/(?:live|shorts|embed|v)/([^/?#]+)", parsed.path)
                video = match.group(1) if match else ""
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", video or ""):
                return {"platform": "youtube", "id": video, "seek": True}
        elif host.endswith("tiktok.com"):
            match = re.search(r"/video/(\d{8,25})", parsed.path)
            if match:
                return {"platform": "tiktok", "id": match.group(1), "seek": True}
        elif host == "fb.watch" or host.endswith("facebook.com"):
            if parsed.scheme == "https":
                return {"platform": "facebook", "id": url, "seek": True}
        elif host.endswith("instagram.com"):
            return {"platform": "instagram", "id": "", "seek": False}
        return {"platform": "", "id": "", "seek": False}

    def _ocd_replay_url_at(self, seconds):
        """Return the link of the replay at the second `seconds`, when the platform allows it
        (YouTube); the link of the replay otherwise."""
        self.ensure_one()
        url = self.replay_url or ""
        host = (urlparse(url).hostname or "").lower()
        if seconds and (host.endswith("youtube.com") or host == "youtu.be"):
            return f"{url}{'&' if '?' in url else '?'}t={int(seconds)}s"
        return url
