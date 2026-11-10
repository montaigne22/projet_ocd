from odoo import api, fields, models


class OcdLiveDashboard(models.AbstractModel):
    """WhatsApp on the dashboard of the team: the conversations waiting for an answer."""

    _inherit = "ocd.live.dashboard"

    @api.model
    def _ocd_waiting_channels(self):
        return self.env["discuss.channel"].search(
            [("channel_type", "=", "whatsapp"), ("whatsapp_waiting_since", "!=", False)],
            order="whatsapp_waiting_since",
        )

    @api.model
    def _ocd_minutes_since(self, value):
        return max(0, int((fields.Datetime.now() - value).total_seconds() // 60))

    @api.model
    def _ocd_tiles(self):
        tiles = super()._ocd_tiles()
        channels = self._ocd_waiting_channels()
        sub = self.env._("Nobody is waiting")
        if channels:
            sub = self.env._(
                "the oldest: %s min", self._ocd_minutes_since(channels[0].whatsapp_waiting_since)
            )
        tiles.append({
            "key": "whatsapp",
            "sequence": 60,
            "label": self.env._("WhatsApp waiting"),
            "value": str(len(channels)),
            "sub": sub,
            "tone": "yellow" if channels else "",
            "action": self._ocd_action("whatsapp_cloud.discuss_channel_action_whatsapp"),
        })
        return tiles

    @api.model
    def _ocd_todos(self):
        todos = super()._ocd_todos()
        channel = self._ocd_waiting_channels()[:1]
        if channel:
            todos.append({
                "key": f"whatsapp_{channel.id}",
                "tag": "WhatsApp",
                "tone": "yellow",
                "text": self.env._(
                    "%(name)s waits for an answer for %(minutes)s min",
                    name=channel.whatsapp_partner_id.name or channel.name,
                    minutes=self._ocd_minutes_since(channel.whatsapp_waiting_since),
                ),
                "action": self._ocd_action("whatsapp_cloud.discuss_channel_action_whatsapp"),
            })
        return todos
