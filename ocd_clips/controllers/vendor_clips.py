"""The clips of the vendor in their space (design ClipsAutomatiques): « My clips » (the last lives,
newest first), the page of a clip (share the video itself with its text, save it, send it to me on
WhatsApp, hide it, make it the video of my card in the feed), the clips of a product from « My
products ». The sentences with values are built whole here."""
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.ocd_live.controllers import common
from odoo.addons.ocd_live_shop.controllers.vendor_products import OcdVendorProducts

# The lives offered as filters of « My clips »
LIVES_SHOWN = 4


def clip_tile(clip):
    """A clip in a grid: its image, its length, the product."""
    return clip._ocd_tile()


def vendor_clips(vendor):
    """The clips the vendor sees: made (hidden ones included), newest live first."""
    return request.env["ocd.live.clip"].sudo().search(
        [("vendor_id", "=", vendor.id), ("state", "=", "ready")],
        order="booking_id desc, start, id",
    )


class OcdVendorClips(http.Controller):

    def _vendor(self):
        return common.current_vendor()

    def _own_clip(self, vendor, clip_id):
        clip = request.env["ocd.live.clip"].sudo().browse(clip_id).exists()
        if not clip or clip.vendor_id != vendor or clip.state != "ready":
            raise request.not_found()
        return clip

    @http.route("/ocd/espace/<string:token>/clips", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def clips_link(self, token, **kwargs):
        """The button of the WhatsApp « your clips are ready »: the personal link opens the space on
        the phone, then « My clips ». (« moi » takes the route below.)"""
        if not common.current_vendor(token):
            return request.redirect("/ocd/connexion")
        live = kwargs.get("live")
        return request.redirect("/ocd/espace/moi/clips" + (f"?live={int(live)}" if str(live or "").isdigit() else ""))

    @http.route("/ocd/espace/moi/clips", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def clips(self, live=None, produit=None, **kwargs):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        clips = vendor_clips(vendor)
        lives = clips.booking_id.sorted("start_datetime", reverse=True)
        chosen_live = lives.filtered(lambda booking: str(booking.id) == str(live))[:1]
        product = env["product.template"]
        if str(produit or "").isdigit():
            product = env["product.template"].sudo().browse(int(produit)).exists()
            if product.ocd_vendor_id != vendor:
                raise request.not_found()
        shown = clips
        if chosen_live:
            shown = shown.filtered(lambda clip: clip.booking_id == chosen_live)
        if product:
            shown = shown.filtered(lambda clip: clip.product_tmpl_id == product)
        filters = [{"label": env._("All"), "url": "/ocd/espace/moi/clips", "on": not chosen_live}] + [{
            "label": env._("Live of %s", clips.filtered(lambda clip: clip.booking_id == booking)[:1]._ocd_live_day("d MMM")),
            "url": f"/ocd/espace/moi/clips?live={booking.id}",
            "on": booking == chosen_live,
        } for booking in lives[:LIVES_SHOWN]]
        if product:
            title = env._("%(product)s · 1 clip", product=product.name) if len(shown) == 1 else env._(
                "%(product)s · %(count)s clips", product=product.name, count=len(shown))
        else:
            title = env._("My clips")
        return request.render("ocd_clips.vendor_clips", common.page_values(
            False,
            space_page="clips",
            back="/ocd/espace/moi/produits" if product else "/ocd/espace/moi",
            back_label=env._("Back to my products") if product else env._("Back to my space"),
            header_title=env._("My clips"),
            vendor=vendor,
            title=title,
            product=product,
            filters=[] if product else filters,
            tiles=[clip_tile(clip) for clip in shown],
            empty_line=env._("Show it in your next live: its clip makes itself.") if product else env._(
                "Your clips come after your next live with OCD: a clip of 30 seconds for each product shown, with its link."
            ),
            off=vendor.ocd_clips_off,
        ))

    @http.route("/ocd/espace/moi/clips/<int:clip_id>", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def clip_page(self, clip_id, fait=None, **kwargs):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        clip = self._own_clip(vendor, clip_id)
        env = request.env
        orders, amount = clip._ocd_sales()
        company = clip.company_id or common.company()
        figures = [
            env._("1 play on the site") if clip.play_count == 1 else env._("%s plays on the site", clip.play_count),
            env._("1 visit by its link") if clip.visit_count == 1 else env._("%s visits by its link", clip.visit_count),
        ]
        if vendor.ocd_sale_mode == "ocd":
            figures.append(env._("1 sale · %s", common.money(amount, company.currency_id)) if orders == 1
                           else env._("%(count)s sales · %(amount)s", count=orders,
                                      amount=common.money(amount, company.currency_id)))
        messages = {
            "masque": env._("Done: this clip no longer shows on the site."),
            "remis": env._("Done: this clip shows again on the site."),
            "carte": env._("Done: this clip is the video of your card in the feed of the lives."),
            "whatsapp": env._("It leaves: the clip arrives in the conversation of OCD Live on WhatsApp."),
        }
        error = {
            "whatsapp": env._("Not sent: %s clips a day at most on WhatsApp. Use « Save », then share it from your phone.",
                              company.ocd_clip_whatsapp_per_day),
            "carte": env._("This clip could not become the video of your card."),
        }.get(kwargs.get("erreur"))
        return request.render("ocd_clips.vendor_clip", common.page_values(
            False,
            space_page="clips",
            back=f"/ocd/espace/moi/clips?produit={clip.product_tmpl_id.id}",
            back_label=env._("Back to my clips"),
            header_title=env._("My clips"),
            vendor=vendor,
            clip=clip,
            video_url=clip._ocd_video_url(),
            download_url=clip._ocd_video_url(download=True),
            poster=clip._ocd_poster_url(),
            line=env._("Live of %(day)s · at %(time)s", day=clip._ocd_live_day("d MMM"), time=clip._ocd_moment_text()),
            live_title=env._("Live of %s", clip._ocd_live_day()),
            figures=figures,
            share_text=clip._ocd_share_text(),
            link=clip._ocd_link(),
            file_name=f"OCD-Live-{clip.code}.mp4",
            whatsapp=clip._ocd_whatsapp_ready(),
            is_card=vendor.ocd_card_media == "video" and vendor.ocd_card_video_name == f"{clip.code}.mp4",
            public=clip._ocd_public(),
            message=messages.get(fait),
            error=error,
        ))

    def _back(self, clip, done=None, error=None):
        query = f"?fait={done}" if done else f"?erreur={error}"
        return request.redirect(f"/ocd/espace/moi/clips/{clip.id}{query}")

    @http.route("/ocd/espace/moi/clips/<int:clip_id>/masquer", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def clip_hide(self, clip_id, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        clip = self._own_clip(vendor, clip_id)
        if clip.hidden:
            clip.action_ocd_show()
            return self._back(clip, "remis")
        clip.write({"hidden": True, "hidden_by": "vendor"})
        return self._back(clip, "masque")

    @http.route("/ocd/espace/moi/clips/<int:clip_id>/carte", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def clip_card(self, clip_id, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        clip = self._own_clip(vendor, clip_id)
        try:
            vendor._ocd_card_video_from_clip(clip)
        except UserError:
            return self._back(clip, error="carte")
        return self._back(clip, "carte")

    @http.route("/ocd/espace/moi/clips/<int:clip_id>/whatsapp", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def clip_whatsapp(self, clip_id, **post):
        """« Send me the clip on WhatsApp »: the video in the conversation of OCD Live, for the
        phones that cannot share a video (a few a day at most)."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        clip = self._own_clip(vendor, clip_id)
        if not clip._ocd_send_to_vendor():
            return self._back(clip, error="whatsapp")
        return self._back(clip, "whatsapp")


class OcdVendorProductsClips(OcdVendorProducts):
    """« My products »: the clips of each product (« ▶ 3 clips ») and « My clips » in its menu « More »."""

    def _rows(self, vendor):
        rows = super()._rows(vendor)
        groups = request.env["ocd.live.clip"].sudo()._read_group(
            [("vendor_id", "=", vendor.id), ("state", "=", "ready")], ["product_tmpl_id"], ["__count"],
        )
        counts = {product.id: count for product, count in groups}
        env = request.env
        any_clip = bool(counts)
        for row in rows:
            count = counts.get(row["product"].id, 0)
            row["clips_count"] = count
            row["clips_label"] = env._("1 clip") if count == 1 else env._("%s clips", count)
            row["clips_url"] = f"/ocd/espace/moi/clips?produit={row['product'].id}"
            # « No clip » once the vendor has clips: the products not shown in a live yet
            row["clips_none"] = any_clip and not count and row["status"] in ("on", "out")
        return rows
