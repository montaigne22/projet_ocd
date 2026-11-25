import re

from odoo import api, models

from odoo.addons.ocd_live import media


class OcdLiveSettings(models.AbstractModel):
    """The automatic clips on the settings page of OCD Live (design ClipsAutomatiques)."""

    _inherit = "ocd.live.settings"

    @api.model
    def _ocd_sections(self):
        return [*super()._ocd_sections(), self._ocd_section_clips()]

    @api.model
    def _ocd_section_clips(self):
        _ = self.env._
        item = self._ocd_item
        Recording = self.env["ocd.live.recording"].sudo()
        free = Recording._ocd_free_bytes() / 1024 ** 3
        server = _(
            "ffmpeg is there; %(free)s GB free for the videos of the lives (1 to 3 GB each, kept a few days).",
            free=f"{free:.1f}",
        ) if media.can_convert() else _(
            "ffmpeg is not installed on the server: the clips cannot be made (pip install -r requirements.txt: imageio-ffmpeg)."
        )
        return {
            "key": "clips",
            "sequence": 43,
            "icon": "CL",
            "label": _("Automatic clips"),
            "title": _("Automatic clips of the lives"),
            "items": [
                item("group", "ocd_clip_lengths", _("Length of a clip"),
                     _("From a little before the moment noted by the control room, cut before the next product."),
                     fields=[
                         item("number", "ocd_clip_max_seconds", _("seconds at most"), min=5, max=60, width=60),
                         item("number", "ocd_clip_before_seconds", _("seconds before the moment"), min=0, max=15, width=60),
                         item("number", "ocd_clip_min_seconds", _("seconds at least, else no clip"), min=5, max=60, width=60),
                     ]),
                item("number", "ocd_clip_keep_days", _("Video of a live kept"),
                     _("To make its clips again; then deleted, the clips stay."), suffix=_("days"), min=1, max=60, width=70),
                item("number", "ocd_clip_keep_removed_months", _("Clips of a product taken off sale"),
                     _("Deleted after this long; the link of the clip leads to the boutique."), suffix=_("months"),
                     min=1, max=36, width=70),
                item("select", "ocd_clip_quality", _("Quality of the clips"),
                     _("720 × 1280: about 6 MB for 30 seconds, quick on mobile data."),
                     options=self._ocd_selection_options("ocd_clip_quality")),
                item("text", "ocd_clip_link_base", _("Address of the short links"),
                     _("Written in the clips before /p/K7Q2AB. Empty: the address of the site."),
                     width=240, size=80),
                item("number", "ocd_clip_whatsapp_per_day", _("« Send me the clip on WhatsApp »"),
                     _("Per vendor and per day."), suffix=_("clips at most"), min=0, max=50, width=70),
                item("info", "ocd_clips_server", _("The server"), server),
                item("info", "ocd_clips_off", _("« No clips » for a vendor"),
                     _("On the form of the vendor, tab « Clips »: no clip is made of their lives, and theirs are no longer shown."),
                     link={"label": _("All the clips"), "action": "ocd_clips.ocd_live_clip_action"}),
            ],
        }

    @api.model
    def _ocd_check_values(self, values):
        errors = super()._ocd_check_values(values)
        link = values.get("ocd_clip_link_base") or ""
        if link and not re.fullmatch(r"https?://[\w.-]+(:\d+)?/?", link):
            errors["ocd_clip_link_base"] = self.env._("Type the address only, beginning with https://.")
        if "ocd_clip_min_seconds" in values and values["ocd_clip_min_seconds"] > values["ocd_clip_max_seconds"]:
            errors["ocd_clip_min_seconds"] = self.env._("Shorter than the length at most.")
        return errors
