from odoo import api, models


class OcdLiveSettings(models.AbstractModel):
    """The big evenings on the settings page of OCD Live."""

    _inherit = "ocd.live.settings"

    @api.model
    def _ocd_sections(self):
        return [*super()._ocd_sections(), self._ocd_section_evenings()]

    @api.model
    def _ocd_section_evenings(self):
        _ = self.env._
        item = self._ocd_item
        return {
            "key": "evenings",
            "sequence": 44,
            "icon": "SO",
            "label": _("Big evenings"),
            "title": _("Big evenings of OCD Live"),
            "items": [
                item("number", "ocd_evening_registration_days", _("Registrations of the vendors"),
                     _("For a new evening: they close these days before it (changed on the evening)."),
                     suffix=_("days before"), min=0, max=60, width=70),
                item("number", "ocd_evening_alert_minutes", _("« Tell me on WhatsApp »"),
                     _("The people who asked are told this long before the start."),
                     suffix=_("minutes before"), min=0, max=1440, width=70),
            ],
        }
