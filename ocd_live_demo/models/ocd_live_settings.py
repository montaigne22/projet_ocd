from odoo import api, models

from .. import hooks, scenario

PLAYED_IN_THE_PAGE = ("youtube", "tiktok", "facebook")


class OcdLiveSettings(models.AbstractModel):
    """Section « Demo » of the settings page: a real video of OCD Live for the replays of the
    demo and a real live link, so that a presentation never opens a video or an account that
    does not exist. Empty, the demo keeps its example links."""

    _inherit = "ocd.live.settings"

    @api.model
    def _ocd_sections(self):
        return [*super()._ocd_sections(), self._ocd_section_demo()]

    @api.model
    def _ocd_section_demo(self):
        _ = self.env._
        item = self._ocd_item
        return {
            "key": "demo",
            "sequence": 95,
            "icon": "DM",
            "label": _("Demo"),
            "title": _("Demo for the presentations"),
            "items": [
                item("text", "ocd_demo_replay_url", _("Video of the replays of the demo"),
                     _("A real video of OCD Live on YouTube, TikTok or Facebook: every replay of the demo plays "
                       "it in the page. Empty: the example links, whose video does not play."),
                     get="_ocd_get_demo_text", set="_ocd_set_demo_replay_url", args=[hooks.PARAM_REPLAY_URL],
                     size=500, width=460, span=2),
                item("number", "ocd_demo_replay_minutes", _("Length of this video"),
                     _("The products shown in the replays are placed along the video."),
                     get="_ocd_get_demo_minutes", set="_ocd_set_demo_minutes",
                     integer=True, min=1, max=600, suffix=_("minutes"), width=70),
                item("text", "ocd_demo_live_url", _("Live link of the demo"),
                     _("The account of OCD Live where its lives are, e.g. https://www.tiktok.com/@ocdlive/live: "
                       "« Watch » on a live of the demo opens it. Empty: the example accounts of the vendors, "
                       "which do not exist."),
                     get="_ocd_get_demo_text", set="_ocd_set_demo_live_url", args=[hooks.PARAM_LIVE_URL],
                     size=500, width=460, span=2),
            ],
        }

    @api.model
    def _ocd_check_values(self, values):
        errors = super()._ocd_check_values(values)
        replay = (values.get("ocd_demo_replay_url") or "").strip()
        if replay:
            embed = self.env["ocd.live.booking"].new({"replay_url": replay})._ocd_replay_embed()
            if embed["platform"] not in PLAYED_IN_THE_PAGE or not embed["id"]:
                errors["ocd_demo_replay_url"] = self.env._(
                    "Paste the link of a video on YouTube, TikTok or Facebook: it plays in the replay page."
                )
        live = (values.get("ocd_demo_live_url") or "").strip()
        if live and not self.env["ocd.live.platform"]._ocd_for_url(live):
            errors["ocd_demo_live_url"] = self.env._(
                "Paste the https link of a live account on %s.", self.env["ocd.live.platform"]._ocd_names_text()
            )
        return errors

    # === VALUES === #

    @api.model
    def _ocd_get_demo_text(self, key):
        return self.env["ir.config_parameter"].sudo().get_str(key) or ""

    @api.model
    def _ocd_get_demo_minutes(self):
        value = self.env["ir.config_parameter"].sudo().get_str(hooks.PARAM_REPLAY_MINUTES) or ""
        return int(value) if value.isdigit() else scenario.REPLAY_MINUTES

    @api.model
    def _ocd_set_demo_replay_url(self, key, value):
        old = self._ocd_set_demo_param(key, value)
        if old is not None:
            hooks.OcdLiveDemo(self.env).apply_media(old_replay=old)

    @api.model
    def _ocd_set_demo_live_url(self, key, value):
        old = self._ocd_set_demo_param(key, value)
        if old is not None:
            hooks.OcdLiveDemo(self.env).apply_media(old_live=old)

    @api.model
    def _ocd_set_demo_minutes(self, value):
        if self._ocd_set_demo_param(hooks.PARAM_REPLAY_MINUTES, str(int(value))) is not None:
            hooks.OcdLiveDemo(self.env).apply_media()

    @api.model
    def _ocd_set_demo_param(self, key, value):
        """Write the setting; return its former value, or None when it did not change."""
        params = self.env["ir.config_parameter"].sudo()
        value = (value or "").strip()
        old = (params.get_str(key) or "").strip()
        if value == old:
            return None
        params.set_str(key, value)
        return old
