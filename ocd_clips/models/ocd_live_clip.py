"""The clip of a product shown in a live (chantier 8, design ClipsAutomatiques): 30 seconds at most
from a little before the moment noted by the control room, cut before the next product, with the
short link of the product. One clip per product and per live.

The clips are made on the server one after the other by a scheduled task: each clip is a task
noted here (its state, 3 tries, the reason of a failure), taken by one worker only, started again
after a restart of the server. A clip shows on the site while its product is on sale and its
vendor active; its link never breaks (the boutique of the vendor or the shop otherwise)."""
import logging
import secrets
from datetime import timedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import BinaryBytes

from .. import clip_video

_logger = logging.getLogger(__name__)

# The letters of the short links: no 0 and O, no 1, I and L
CODE_LETTERS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CODE_LENGTH = 6
TRIES = 3
# A clip « being made » for longer: its worker stopped, it is made again
STUCK_MINUTES = 30
STATES = [
    ("queued", "To Make"),
    ("processing", "Being Made"),
    ("ready", "Ready"),
    ("failed", "Not Made"),
    ("skipped", "No Clip"),
]
REASONS = [
    ("too_close", "The next product comes too soon"),
    ("outside", "Not in the video of the live"),
    ("no_video", "The video of the live is deleted"),
    ("unreadable", "The video cannot be read"),
    ("failed", "The video could not be made"),
]


class OcdLiveClip(models.Model):
    _name = "ocd.live.clip"
    _description = "Clip Of A Product Of A Live"
    _order = "booking_id desc, start, id"

    booking_id = fields.Many2one(comodel_name="ocd.live.booking", string="Live", required=True, index=True,
                                 ondelete="cascade")
    company_id = fields.Many2one(related="booking_id.company_id", store=True)
    vendor_id = fields.Many2one(related="booking_id.partner_id", string="Vendor", store=True, index=True)
    moment_id = fields.Many2one(comodel_name="ocd.live.moment", string="Moment", ondelete="set null")
    product_tmpl_id = fields.Many2one(comodel_name="product.template", string="Product", required=True, index=True,
                                      ondelete="cascade")
    product_id = fields.Many2one(comodel_name="product.product", string="Colour Shown", ondelete="set null")
    code = fields.Char(string="Short Link", required=True, copy=False, index=True, readonly=True,
                       default=lambda self: self._ocd_new_code())
    start = fields.Float(string="From (Seconds Of The Live)", digits=(16, 1))
    duration = fields.Float(string="Length (Seconds)", digits=(16, 1))
    state = fields.Selection(selection=STATES, required=True, default="queued", index=True)
    reason = fields.Selection(selection=REASONS, string="Why")
    error = fields.Char(readonly=True)
    tries = fields.Integer(readonly=True)
    processing_since = fields.Datetime(readonly=True)
    made_at = fields.Datetime(string="Made At", readonly=True)
    version = fields.Integer(default=0, readonly=True, help="Changes with the video (the address seen by the CDN).")
    video = fields.Binary(string="Video", attachment=True, readonly=True)
    poster = fields.Binary(string="Image", attachment=True, readonly=True)
    video_size = fields.Integer(string="Size (Bytes)", readonly=True)
    hidden = fields.Boolean(string="Hidden", index=True)
    hidden_by = fields.Selection(selection=[("vendor", "The Vendor"), ("team", "The Team")], readonly=True)
    play_count = fields.Integer(string="Plays", compute="_compute_figures")
    visit_count = fields.Integer(string="Visits", compute="_compute_figures")
    order_count = fields.Integer(string="Sales", compute="_compute_figures")

    _unique_code = models.UniqueIndex("(code)", "Another clip has this short link.")
    _unique_product = models.UniqueIndex("(booking_id, product_tmpl_id)", "One clip per product and per live.")

    @api.model
    def _ocd_new_code(self):
        while True:
            code = "".join(secrets.choice(CODE_LETTERS) for _index in range(CODE_LENGTH))
            if not self.sudo().with_context(active_test=False).search_count([("code", "=", code)]):
                return code

    def _compute_figures(self):
        Count = self.env["ocd.vendor.count"]
        lines = self.env["sale.order.line"].sudo()._read_group(
            [("ocd_clip_id", "in", self.ids), ("order_id.state", "=", "sale")], ["ocd_clip_id"], ["order_id:count_distinct"],
        )
        orders = {clip.id: count for clip, count in lines}
        by_vendor = {}
        for clip in self:
            by_vendor.setdefault(clip.vendor_id, self.browse())
            by_vendor[clip.vendor_id] |= clip
        plays, visits = {}, {}
        for vendor, clips in by_vendor.items():
            if vendor:
                plays.update(Count._ocd_record_totals(vendor, "clip_play", clips.ids))
                visits.update(Count._ocd_record_totals(vendor, "clip_visit", clips.ids))
        for clip in self:
            clip.play_count = plays.get(clip.id, 0)
            clip.visit_count = visits.get(clip.id, 0)
            clip.order_count = orders.get(clip.id, 0)

    @api.depends("product_tmpl_id", "booking_id")
    def _compute_display_name(self):
        for clip in self:
            clip.display_name = " · ".join(part for part in (clip.product_tmpl_id.name, clip.booking_id.display_name) if part)

    # === WHERE IT IS SEEN === #

    def _ocd_public(self):
        """Whether the clip shows on the site: made, not hidden, its product on sale and its
        vendor active, the clips of the vendor not turned off."""
        self.ensure_one()
        product = self.product_tmpl_id.sudo()
        vendor = self.vendor_id.sudo()
        return (
            self.state == "ready" and not self.hidden and bool(self.video)
            and product.active and product.sale_ok and product.is_published and product.ocd_review_state == "approved"
            and vendor.ocd_is_vendor and vendor.ocd_vendor_state == "approved" and not vendor.ocd_clips_off
        )

    @api.model
    def _ocd_public_domain(self):
        return Domain([
            ("state", "=", "ready"), ("hidden", "=", False), ("product_tmpl_id.active", "=", True),
            ("product_tmpl_id.sale_ok", "=", True), ("product_tmpl_id.is_published", "=", True),
            ("product_tmpl_id.ocd_review_state", "=", "approved"), ("vendor_id.ocd_vendor_state", "=", "approved"),
            ("vendor_id.ocd_clips_off", "=", False),
        ])

    def _ocd_base_url(self):
        """The address of the short links: the setting, else the address of the site."""
        company = self.company_id or self.env.company
        return (company.ocd_clip_link_base or self.get_base_url() or "").strip().rstrip("/")

    def _ocd_link(self):
        """The short link: https://<site>/p/K7Q2AB."""
        self.ensure_one()
        return f"{self._ocd_base_url()}/p/{self.code}"

    def _ocd_link_text(self):
        """The short link as written in the video and the text: « ocdlive.com/p/K7Q2AB »."""
        self.ensure_one()
        return self._ocd_link().split("://", 1)[-1]

    def _ocd_video_url(self, download=False):
        self.ensure_one()
        return f"/ocd/clips/{self.id}/video?v={self.version}" + ("&dl=1" if download else "")

    def _ocd_poster_url(self):
        self.ensure_one()
        return f"/ocd/clips/{self.id}/image?v={self.version}" if self.poster else False

    def _ocd_duration_text(self):
        self.ensure_one()
        seconds = int(round(self.duration or 0))
        return f"{seconds // 60}:{seconds % 60:02d}"

    def _ocd_moment_text(self):
        """« 04:12 »: where the product is shown in the live."""
        self.ensure_one()
        offset = self.moment_id.offset_seconds if self.moment_id else int(self.start)
        return self.env["ocd.live.moment"]._ocd_time_label(offset)

    def _ocd_share_text(self, lang=None):
        """The text copied with the clip: the product, its price of now, the vendor, the link."""
        self.ensure_one()
        env = self.with_context(lang=lang or self.vendor_id.lang or self.env.lang).env
        product = self.product_tmpl_id.sudo().with_env(env)
        price, _was = product._ocd_on_sale_price()
        from odoo.addons.ocd_live.controllers import common  # noqa: PLC0415 (a page helper)

        money = common.money(price, product.currency_id)
        vendor = self.vendor_id
        if vendor.ocd_sale_mode == "ocd":
            return env._(
                "%(product)s, %(price)s at %(vendor)s. Order here: %(link)s · Delivery with a code, you pay at the door. #OCDLive",
                product=product.name, price=money, vendor=vendor.name, link=self._ocd_link_text(),
            )
        return env._(
            "%(product)s, %(price)s at %(vendor)s. See it here: %(link)s #OCDLive",
            product=product.name, price=money, vendor=vendor.name, link=self._ocd_link_text(),
        )

    # === MAKING === #

    def _ocd_texts(self):
        """The texts drawn on the clip, in the language of the vendor."""
        self.ensure_one()
        vendor = self.vendor_id
        env = self.with_context(lang=vendor.lang or self.env.lang).env
        product = self.product_tmpl_id.sudo().with_env(env)
        city = vendor.city or vendor.country_id.name or ""
        return {
            "name": product.name,
            "by": " · ".join(part for part in (vendor.name, city) if part),
            "link": self._ocd_link_text(),
            "url": self._ocd_link(),
            "seen": env._("Seen in live"),
            "line": env._("Delivery with a code, you pay at the door") if vendor.ocd_sale_mode == "ocd"
            else env._("Order on OCD Live"),
        }

    def _ocd_part(self):
        """The part of the video of the live that holds the clip."""
        self.ensure_one()
        return self.booking_id.ocd_recording_ids.filtered(lambda part: part._ocd_contains(self.start, self.duration))[:1]

    def _ocd_make(self):
        """Make the video of the clip; return whether it is made. A failure is noted, tried
        again later (3 tries), then the clip stays « Not made » with its reason."""
        self.ensure_one()
        part = self._ocd_part()
        if not part or not part._ocd_has_file():
            gone = self.booking_id.ocd_recording_ids.filtered(lambda part: part.state == "deleted")
            self.write({
                "state": "failed", "reason": "no_video" if gone else "outside", "processing_since": False,
                "error": self.env._("The video of the live is no longer on the server (deleted after its days).")
                if gone else self.env._("Not in the video of the live: check its shift or send the next part."),
            })
            return False
        quality = (self.company_id or self.env.company).ocd_clip_quality or "720"
        texts = self._ocd_texts()
        try:
            info = {"width": part.width, "height": part.height, "sound": part.has_sound}
            video, poster = clip_video.make(
                part._ocd_path(), self.start - part.offset_seconds, self.duration, info,
                clip_video.overlay(texts, quality), clip_video.end_card(texts, quality), quality,
            )
        except clip_video.ClipError as error:
            tries = self.tries + 1
            message = {
                "no_ffmpeg": self.env._("ffmpeg is not installed on the server."),
                "too_slow": self.env._("The server took too long to make the clip."),
            }.get(error.code, self.env._("The video could not be made (ffmpeg)."))
            self.write({
                "tries": tries, "error": message, "processing_since": False,
                "state": "queued" if tries < TRIES and error.code != "no_ffmpeg" else "failed",
                "reason": "failed",
            })
            return False
        self.write({
            "video": BinaryBytes(video, filename=f"{self.code}.mp4"),
            "poster": BinaryBytes(poster) if poster else False,
            "video_size": len(video),
            "state": "ready",
            "reason": False,
            "error": False,
            "tries": self.tries + 1,
            "processing_since": False,
            "made_at": fields.Datetime.now(),
            "version": self.version + 1,
        })
        return True

    def action_ocd_remake(self):
        """« Make again »: the clip is made again with the shift and the texts of now."""
        for clip in self.filtered(lambda clip: clip.state not in ("processing",)):
            clip.write({"state": "queued", "tries": 0, "error": False, "reason": False})
        self.env["ocd.live.recording"]._ocd_trigger()
        return True

    def action_ocd_hide(self):
        self.write({"hidden": True, "hidden_by": "team" if self.env.user._is_internal() else "vendor"})
        return True

    def action_ocd_show(self):
        self.write({"hidden": False, "hidden_by": False})
        return True

    @api.model
    def _cron_ocd_clips(self):
        """Every few minutes and when a video arrives: the videos received are checked, then the
        clips are made one after the other, each kept as soon as it is made."""
        Recording = self.env["ocd.live.recording"].sudo()
        cron = self.env["ir.cron"]
        Recording.search([("state", "=", "checking")])._ocd_check()
        # A worker stopped while making a clip: it is made again
        self.sudo().search([
            ("state", "=", "processing"),
            ("processing_since", "<", fields.Datetime.now() - timedelta(minutes=STUCK_MINUTES)),
        ]).write({"state": "queued", "processing_since": False})
        remaining = self.sudo().search_count([("state", "=", "queued")])
        cron._commit_progress(remaining=remaining)
        while True:
            clip = self._ocd_take_one()
            if not clip:
                break
            clip._ocd_make()
            clip.booking_id._ocd_clips_done()
            if not cron._commit_progress(1):
                break  # no time left: the next run goes on
        Recording._ocd_clean()
        self._ocd_clean()

    @api.model
    def _ocd_take_one(self):
        """The next clip to make, taken by this worker only (the others skip it)."""
        self.env.cr.execute("""
            SELECT id FROM ocd_live_clip WHERE state = 'queued' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED
        """)
        row = self.env.cr.fetchone()
        if not row:
            return self.browse()
        clip = self.sudo().browse(row[0])
        clip.write({"state": "processing", "processing_since": fields.Datetime.now()})
        return clip

    @api.model
    def _ocd_clean(self):
        """The clips of a product removed from the sale for long (setting) are deleted."""
        company = self.env.company
        limit = fields.Datetime.now() - timedelta(days=company.ocd_clip_keep_removed_days or 90)
        old = self.sudo().with_context(active_test=False).search([
            ("product_tmpl_id.active", "=", False), ("product_tmpl_id.write_date", "<", limit),
        ])
        old.unlink()
