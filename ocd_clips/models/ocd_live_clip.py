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
from odoo.tools.misc import format_amount

from odoo.addons.ocd_live import tools

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
    ("deleted", "Video Deleted"),
]
ERRORS = [
    ("no_video", "The video of the live is deleted"),
    ("outside", "Not in the video of the live"),
    ("no_ffmpeg", "ffmpeg is not installed"),
    ("too_slow", "Too long to make"),
    ("ffmpeg", "ffmpeg failed"),
    ("stopped", "The server stopped"),
    ("crash", "Unexpected error"),
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
    error_code = fields.Selection(selection=ERRORS, string="What Happened", readonly=True)
    error_detail = fields.Char(string="Detail", readonly=True, help="The message of the server, for the developers.")
    # Written in the language of the person who reads it (the clips are made by a scheduled task)
    error = fields.Char(compute="_compute_error")
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

    def _compute_error(self):
        _ = self.env._
        messages = {
            "no_video": _("The video of the live is no longer on the server (deleted after its days)."),
            "outside": _("Not in the video of the live: check its shift or send the next part."),
            "no_ffmpeg": _("ffmpeg is not installed on the server."),
            "too_slow": _("The server took too long to make the clip."),
            "ffmpeg": _("The video could not be made (ffmpeg)."),
            "stopped": _("The server stopped while making the clip."),
        }
        for clip in self:
            if clip.error_code == "crash":
                clip.error = _("The clip could not be made: %s", clip.error_detail or "")
            else:
                clip.error = messages.get(clip.error_code, False)

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
            self.state == "ready" and not self.hidden and bool(self.video_size)
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

    def _ocd_live_day(self, pattern="EEEE d MMMM"):
        """The day of the live at the hour of the vendor: « mardi 17 novembre »."""
        self.ensure_one()
        booking = self.booking_id.sudo()
        local = tools.to_tz(booking.start_datetime, self.vendor_id.sudo()._ocd_tz_name())
        return tools.day_text(self.env, local.date(), pattern)

    def _ocd_on_sale(self):
        """Whether the product of the clip is on sale on the site, its vendor active."""
        self.ensure_one()
        product = self.product_tmpl_id.sudo()
        vendor = self.vendor_id.sudo()
        return (product.active and product.sale_ok and product.is_published and product.ocd_review_state == "approved"
                and vendor.ocd_vendor_state == "approved")

    def _ocd_target_url(self):
        """Where the short link leads: the product with the colour shown; else the boutique of the
        vendor, else the shop. Never an error: a clip lives months on TikTok."""
        self.ensure_one()
        if self._ocd_on_sale():
            query = self.moment_id._ocd_variant_query() if self.moment_id else ""
            return self.product_tmpl_id.sudo().website_url + query
        vendor = self.vendor_id.sudo()
        if vendor.ocd_is_vendor and vendor.ocd_vendor_state == "approved":
            return f"/ocd/boutique/{vendor.id}"
        return "/shop"

    def _ocd_replay_url(self):
        """The replay of the live at the moment of the product, when it is published."""
        self.ensure_one()
        booking = self.booking_id.sudo()
        if not booking.replay_published or not booking.replay_url:
            return False
        seconds = self.moment_id.offset_seconds if self.moment_id else int(self.start)
        return f"/ocd/boutique/{booking.partner_id.id}/replay?live={booking.id}&t={seconds}"

    def _ocd_sales(self):
        """(orders, amount) of the confirmed orders that came by the clip, in the currency of the
        company."""
        self.ensure_one()
        lines = self.env["sale.order.line"].sudo().search([
            ("ocd_clip_id", "=", self.id), ("order_id.state", "=", "sale"),
        ])
        company = self.company_id or self.env.company
        amount = sum(
            line.currency_id._convert(line.price_total, company.currency_id, company, line.order_id.date_order)
            for line in lines
        )
        return len(lines.order_id), amount

    def _ocd_share_text(self, lang=None):
        """The text copied with the clip: the product, its price of now, the vendor, the link."""
        self.ensure_one()
        env = self.with_context(lang=lang or self.vendor_id.lang or self.env.lang).env
        product = self.product_tmpl_id.sudo().with_env(env)
        price, _was = product._ocd_on_sale_price()
        money = format_amount(env, price, product.currency_id)
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

    # === ON THE PAGES === #

    def _ocd_tile(self):
        """The clip in a grid of the space of the vendor: its image, its length, the product."""
        self.ensure_one()
        return {
            "clip": self,
            "url": f"/ocd/espace/moi/clips/{self.id}",
            "poster": self._ocd_poster_url(),
            "length": self._ocd_duration_text(),
            "name": self.product_tmpl_id.name,
            "caption": self.env._("%s · hidden", self.product_tmpl_id.name) if self.hidden else self.product_tmpl_id.name,
            "hidden": self.hidden,
        }

    @api.model
    def _ocd_space_card(self, vendor, days=7):
        """« Your clips are ready » in « My space »: the last live of the vendor whose clips were
        made these last days, with three of them."""
        if not vendor or vendor.ocd_clips_off:
            return False
        clips = self.sudo().search([
            ("vendor_id", "=", vendor.id), ("state", "=", "ready"),
            ("made_at", ">", fields.Datetime.now() - timedelta(days=days)),
        ], order="booking_id desc, start, id")
        if not clips:
            return False
        booking = clips[0].booking_id
        clips = clips.filtered(lambda clip: clip.booking_id == booking)
        env = self.env
        place = env._("studio of %s", (booking.company_id or env.company).ocd_studio_city or "Lomé") \
            if booking.mode == "studio" else env._("remote")
        return {
            "kicker": env._("Live of %(day)s · %(place)s", day=clips[0]._ocd_live_day(), place=place),
            "title": env._("Your clip is ready") if len(clips) == 1 else env._("Your %s clips are ready", len(clips)),
            "tiles": [clip._ocd_tile() for clip in clips[:3]],
            "url": f"/ocd/espace/moi/clips?live={booking.id}",
        }

    def _ocd_public_media(self):
        """The video and the image of a clip shown to everyone: by the CDN when the site has one."""
        self.ensure_one()
        video, poster = self._ocd_video_url(), self._ocd_poster_url()
        website = self.env.website
        if not website:
            return video, poster
        return website._ocd_cdn_url(video), website._ocd_cdn_url(poster)

    @api.model
    def _ocd_seen_in_live(self, template):
        """« Seen in live » on the product page: the newest clip of the product shown on the site,
        played only at the touch."""
        if not template:
            return False
        clip = self.sudo().search(
            Domain(self._ocd_public_domain()) & Domain("product_tmpl_id", "=", template.id),
            order="made_at desc, id desc", limit=1,
        )
        if not clip or not clip._ocd_public():
            return False
        video, poster = clip._ocd_public_media()
        return {
            "video": video,
            "poster": poster,
            "length": clip._ocd_duration_text(),
            "count_url": f"/ocd/clips/{clip.id}/lu",
            "aria": self.env._("Play the clip of the live"),
            "line": self.env._(
                "In their live of %(day)s, %(vendor)s presents this product. Touch to watch it (the video loads only then).",
                day=clip._ocd_live_day(), vendor=clip.vendor_id.name,
            ),
            "replay": clip._ocd_replay_url(),
        }

    @api.model
    def _ocd_replay_clips(self, booking):
        """The clip of each product of a replay shown on the site: {product id: clip}."""
        if not booking:
            return {}
        clips = self.sudo().search(Domain(self._ocd_public_domain()) & Domain("booking_id", "=", booking.id))
        result = {}
        for clip in clips.filtered(lambda clip: clip._ocd_public()):
            video, poster = clip._ocd_public_media()
            result[clip.product_tmpl_id.id] = {
                "video": video,
                "poster": poster,
                "count_url": f"/ocd/clips/{clip.id}/lu",
                "aria": self.env._("Play the clip of %s", clip.product_tmpl_id.name),
            }
        return result

    @api.model
    def _ocd_figures(self, vendor, days, now=None):
        """« From my clips » in « My figures »: the visits by the short links, the plays on the site
        and the sales of the last `days` days, the clip that brought most. False without clips."""
        vendor = vendor.sudo()
        if not vendor or not self.sudo().search_count([("vendor_id", "=", vendor.id), ("state", "in", ("ready", "deleted"))]):
            return False
        now = now or fields.Datetime.now()
        Count = self.env["ocd.vendor.count"]
        Figures = self.env["ocd.vendor.figures"]
        today = tools.to_tz(now, vendor._ocd_tz_name()).date()
        first = today - timedelta(days=days - 1)
        visits = Count._ocd_totals(vendor, "clip_visit", first, today, by_record=True)
        plays = Count._ocd_totals(vendor, "clip_play", first, today)
        lines = Figures._ocd_lines(vendor, now - timedelta(days=days), now).filtered("ocd_clip_id")
        currency = Figures._ocd_currency(vendor)
        sums = Figures._ocd_sums(lines, currency)
        _ = self.env._
        best = False
        if visits:
            clip_id, count = max(visits.items(), key=lambda item: item[1])
            clip = self.sudo().browse(clip_id).exists()
            if clip and count:
                best = _("1 visit") if count == 1 else _("%s visits", Figures._ocd_number(count))
                best = _("Best clip: %(product)s, live of %(day)s (%(visits)s)", product=clip.product_tmpl_id.name,
                         day=clip._ocd_live_day("d MMM"), visits=best)
        return {
            "visits": Figures._ocd_number(sum(visits.values())),
            "plays": Figures._ocd_number(plays),
            "sales": _("1 sale · %s", Figures._ocd_money(sums["amount"], currency)) if sums["orders"] == 1
            else _("%(count)s sales · %(amount)s", count=sums["orders"], amount=Figures._ocd_money(sums["amount"], currency)),
            "best": best,
        }

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
        """Make the video of the clip (its try is counted when it is taken); return whether it is
        made. A failure is noted, tried again by the next run (3 tries), then the clip stays
        « Not made » with its reason."""
        self.ensure_one()
        part = self._ocd_part()
        if not part or not part._ocd_has_file():
            gone = self.booking_id.ocd_recording_ids.filtered(lambda part: part.state == "deleted")
            self.write({
                "state": "failed", "reason": "no_video" if gone else "outside", "processing_since": False,
                "error_code": "no_video" if gone else "outside", "error_detail": False,
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
            code = error.code if error.code in ("no_ffmpeg", "too_slow") else "ffmpeg"
            self._ocd_failed_try(code, detail=error.values.get("detail"), final=code == "no_ffmpeg")
            return False
        self.write({
            "video": BinaryBytes(video, filename=f"{self.code}.mp4"),
            "poster": BinaryBytes(poster) if poster else False,
            "video_size": len(video),
            "state": "ready",
            "reason": False,
            "error_code": False,
            "error_detail": False,
            "processing_since": False,
            "made_at": fields.Datetime.now(),
            "version": self.version + 1,
        })
        return True

    def _ocd_failed_try(self, code, detail=None, final=False):
        """A try that failed (`code` of ERRORS): the clip waits for the next run, « Not made »
        after 3 tries."""
        for clip in self:
            clip.write({
                "error_code": code, "error_detail": (detail or "")[:300] or False, "processing_since": False,
                "reason": "failed", "state": "queued" if clip.tries < TRIES and not final else "failed",
            })

    # === SEND ME THE CLIP ON WHATSAPP === #

    def _ocd_whatsapp_ready(self):
        """Whether « Send me the clip on WhatsApp » is offered (ocd_clips_whatsapp)."""
        return False

    def _ocd_send_to_vendor(self):
        """« Send me the clip on WhatsApp »: the clip in the conversation of OCD Live, a few a day
        per vendor (setting). Return whether it leaves."""
        self.ensure_one()
        vendor = self.vendor_id.sudo()
        company = self.company_id or self.env.company
        today = fields.Date.context_today(vendor.with_context(tz=vendor._ocd_tz_name()))
        sent = vendor.ocd_clips_sent_count if vendor.ocd_clips_sent_day == today else 0
        if sent >= company.ocd_clip_whatsapp_per_day or not self._ocd_whatsapp_ready():
            return False
        if not self._ocd_whatsapp_clip():
            return False
        vendor.write({"ocd_clips_sent_day": today, "ocd_clips_sent_count": sent + 1})
        return True

    def _ocd_whatsapp_clip(self):
        """Hook (ocd_clips_whatsapp): send the clip to its vendor; return whether it leaves."""
        return False

    def action_ocd_remake(self):
        """« Make again »: the clip is made again with the shift and the texts of now."""
        for clip in self.filtered(lambda clip: clip.state not in ("processing",)):
            clip.write({"state": "queued", "tries": 0, "error_code": False, "error_detail": False, "reason": False})
        self.env["ocd.live.recording"]._ocd_trigger()
        return True

    def action_ocd_open_screen(self):
        """The screen of the video of the live and its clips."""
        self.ensure_one()
        return self.booking_id.action_ocd_open_clips()

    def action_ocd_open_link(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": self._ocd_link(), "target": "new"}

    def action_ocd_hide(self):
        self.write({"hidden": True, "hidden_by": "team" if self.env.user._is_internal() else "vendor"})
        return True

    def action_ocd_show(self):
        self.write({"hidden": False, "hidden_by": False})
        return True

    @api.model
    def _cron_ocd_clips(self):
        """Every few minutes and when a video arrives: the videos received are checked, then the
        clips are made one after the other, each kept as soon as it is made. A clip that fails
        waits for the next run; a clip taken by a worker that stopped (a restart of the server)
        is taken again, its try counted."""
        Recording = self.env["ocd.live.recording"].sudo()
        cron = self.env["ir.cron"]
        Recording.search([("state", "=", "checking")])._ocd_check()
        stuck = self.sudo().search([
            ("state", "=", "processing"),
            ("processing_since", "<", fields.Datetime.now() - timedelta(minutes=STUCK_MINUTES)),
        ])
        stuck._ocd_failed_try("stopped")
        remaining = self.sudo().search_count([("state", "=", "queued")])
        cron._commit_progress(remaining=remaining)
        tried = []
        while True:
            clip = self._ocd_take_one(tried)
            if not clip:
                break
            tried.append(clip.id)
            try:
                with self.env.cr.savepoint():
                    clip._ocd_make()
            except Exception as error:  # noqa: BLE001 - a clip never stops the others
                _logger.exception("OCD Live: clip %s not made", clip.id)
                clip.invalidate_recordset()
                clip._ocd_failed_try("crash", detail=str(error))
            clip.booking_id._ocd_clips_done()
            if not cron._commit_progress(1):
                break  # no time left: the next run goes on
        Recording._ocd_clean()
        self._ocd_clean()

    @api.model
    def _ocd_take_one(self, tried=()):
        """The next clip to make, taken by this worker only (the others skip it), the clips of a
        live together; its try is counted. Not one tried already by this run."""
        self.env["ocd.live.clip"].flush_model(["state"])  # the states written before, seen by the query
        self.env.cr.execute("""
            SELECT id FROM ocd_live_clip WHERE state = 'queued' AND NOT (id = ANY(%s))
             ORDER BY booking_id, id LIMIT 1 FOR UPDATE SKIP LOCKED
        """, [list(tried)])
        row = self.env.cr.fetchone()
        if not row:
            return self.browse()
        clip = self.sudo().browse(row[0])
        clip.write({"state": "processing", "processing_since": fields.Datetime.now(), "tries": clip.tries + 1})
        return clip

    @api.model
    def _ocd_clean(self):
        """The videos of the clips of a product taken off sale for long (setting, in months) are
        deleted; their short link leads to the boutique of the vendor (or the shop) from then on."""
        company = self.env.company
        limit = fields.Datetime.now() - timedelta(days=30 * (company.ocd_clip_keep_removed_months or 3))
        old = self.sudo().with_context(active_test=False).search([
            ("state", "=", "ready"),
            "|", "|", ("product_tmpl_id.active", "=", False), ("product_tmpl_id.ocd_vendor_retired", "=", True),
            ("product_tmpl_id.sale_ok", "=", False), ("product_tmpl_id.write_date", "<", limit),
        ])
        # The clip stays without its video: its short link still leads to the boutique
        old.write({"video": False, "poster": False, "video_size": 0, "state": "deleted"})
