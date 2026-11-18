"""The clips on the site (design ClipsAutomatiques):

- the video of a live sent by the team in pieces (/ocd/clips/envoi), its preview;
- the video and the image of a clip, kept by the phones and the CDN while it shows on the site;
- the short link /p/<code>: one visit per phone and per day, without the robots (the previews of
  the links of WhatsApp and TikTok), to the product with the colour shown, else the boutique or
  the shop; the phone keeps the clip 7 days for the sales it brings (sale_order.py);
- a play on the product page or the replay, counted for the vendor."""
import re

from odoo import fields, http
from odoo.http import request

from odoo.addons.ocd_live import page_cache
from odoo.addons.ocd_live.controllers import common
from odoo.addons.website_sale.models.website import CART_SESSION_CACHE_KEY

from .. import clip_video
from ..models.sale_order import SESSION_KEY, visits_kept

# The visits of the clips change no public page: the pages stay kept in memory for these visitors
page_cache.SESSION_KEYS = page_cache.SESSION_KEYS | {SESSION_KEY}

# The robots that open the links (previews of WhatsApp, Facebook, TikTok, search engines): no visit
ROBOTS = re.compile(
    r"bot|crawl|spider|slurp|preview|facebookexternalhit|facebookcatalog|whatsapp|telegram|discord|skype|"
    r"bytespider|tiktok|embedly|quora link|pinterest|vkshare|w3c_validator|curl|wget|python-requests|headless",
    re.IGNORECASE,
)


def is_robot():
    agent = request.httprequest.headers.get("User-Agent") or ""
    return not agent or bool(ROBOTS.search(agent))


class OcdClips(http.Controller):

    # === THE VIDEO OF A LIVE, SENT BY THE TEAM === #

    @http.route("/ocd/clips/envoi/<int:part_id>", type="http", auth="user", methods=["POST"], csrf=False, sitemap=False)
    def upload_piece(self, part_id, token=None, offset=None, **kwargs):
        """A piece of the video of a live (8 MB at most) at `offset`: answers the bytes received
        so far, from where the browser goes on. The token of the part replaces the token of the
        forms (the pieces are not forms)."""
        if not request.env.user.has_group("ocd_live.group_ocd_live_user"):
            raise request.not_found()
        part = request.env["ocd.live.recording"].sudo().browse(part_id).exists()
        if not part or not token or not part.token or token != part.token:
            raise request.not_found()
        try:
            offset = int(offset or 0)
        except ValueError:
            offset = -1
        received = part._ocd_write_piece(offset, request.httprequest.get_data(cache=False))
        return request.make_json_response({"received": received, "state": part.state})

    @http.route("/ocd/clips/apercu/<int:booking_id>", type="http", auth="user", methods=["GET"], sitemap=False)
    def preview(self, booking_id, **kwargs):
        """8 seconds of the video of the live from a little before its first moment, to check the
        shift of the recording."""
        if not request.env.user.has_group("ocd_live.group_ocd_live_user"):
            raise request.not_found()
        booking = request.env["ocd.live.booking"].sudo().browse(booking_id).exists()
        found = booking.ocd_clips_preview_info() if booking else False
        if not found:
            raise request.not_found()
        part, start = found
        info = {"width": part.width, "height": part.height, "sound": part.has_sound}
        try:
            video = clip_video.preview(part._ocd_path(), start, info)
        except clip_video.ClipError:
            raise request.not_found() from None
        return request.make_response(video, headers=[
            ("Content-Type", "video/mp4"), ("Content-Length", str(len(video))), ("Cache-Control", "no-store"),
        ])

    # === THE CLIP: ITS VIDEO AND ITS IMAGE === #

    def _clip_media(self, clip_id, field):
        """The clip whose `field` is asked: everyone while it shows on the site; its vendor and
        the team always (a hidden clip, a product being checked)."""
        clip = request.env["ocd.live.clip"].sudo().browse(clip_id).exists()
        if not clip or not clip[field] or clip.state != "ready":
            raise request.not_found()
        public = clip._ocd_public()
        if not public and not (common.current_vendor() == clip.vendor_id or request.env.user._is_internal()):
            raise request.not_found()
        return clip, public

    @http.route("/ocd/clips/<int:clip_id>/video", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def clip_video(self, clip_id, dl=None, **kwargs):
        """The video of the clip (the phones ask it by parts); `dl=1`: to save it in the phone."""
        clip, public = self._clip_media(clip_id, "video")
        stream = request.env["ir.binary"]._get_stream_from(clip, "video")
        stream.download_name = f"OCD-Live-{clip.code}.mp4"
        stream.mimetype = "video/mp4"
        return common.media_response(stream, public=public, version=clip.version, content_security_policy=None,
                                     as_attachment=bool(dl))

    @http.route("/ocd/clips/<int:clip_id>/image", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def clip_image(self, clip_id, **kwargs):
        clip, public = self._clip_media(clip_id, "poster")
        stream = request.env["ir.binary"]._get_image_stream_from(clip, "poster")
        return common.media_response(stream, public=public, version=clip.version)

    @http.route("/ocd/clips/<int:clip_id>/lu", type="http", auth="public", website=True, methods=["POST"], csrf=False,
                sitemap=False)
    def clip_played(self, clip_id, **kwargs):
        """A clip played on the product page or the replay (told by the page once per view):
        counted for the vendor, never their own plays nor the robots."""
        clip = request.env["ocd.live.clip"].sudo().browse(clip_id).exists()
        if clip and clip._ocd_public() and not is_robot() and common.current_vendor() != clip.vendor_id:
            request.env["ocd.vendor.count"]._ocd_add(clip.vendor_id, "clip_play", clip.id)
        return request.make_response("", status=204)

    # === THE SHORT LINK === #

    @http.route("/p/<string:code>", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def short_link(self, code, **kwargs):
        clip = request.env["ocd.live.clip"].sudo().search([("code", "=", (code or "").strip().upper()[:12])], limit=1)
        if not clip:
            response = request.redirect("/shop", code=302)
        else:
            if not is_robot() and common.current_vendor() != clip.vendor_id and not request.env.user._is_internal():
                self._count_visit(clip)
            response = request.redirect(clip._ocd_target_url(), code=302)
        response.headers["X-Robots-Tag"] = "noindex"
        response.headers["Cache-Control"] = "no-store"
        return response

    def _count_visit(self, clip):
        """One visit per phone and per day; the phone keeps the clip 7 days (its sales)."""
        now = fields.Datetime.now()
        visits = visits_kept(request.session.get(SESSION_KEY), now)
        last = visits.get(str(clip.id))
        if not last or last[:10] != now.date().isoformat():
            request.env["ocd.vendor.count"]._ocd_add(clip.vendor_id, "clip_visit", clip.id)
        visits[str(clip.id)] = now.isoformat(timespec="seconds")
        visits = visits_kept(visits, now)
        request.session[SESSION_KEY] = visits
        cart_id = request.session.get(CART_SESSION_CACHE_KEY)
        if cart_id:
            request.env["sale.order"].sudo().browse(cart_id).exists()._ocd_note_clips(visits)
