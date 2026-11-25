from odoo import api, fields, models
from odoo.tools.misc import format_date

# The periods of the figures of the conversations (days), the first one shown at first
STATS_DAYS = (7, 30)


class OcdLiveDashboard(models.AbstractModel):
    """WhatsApp on the dashboard of the team: the conversations waiting for an answer, and the
    figures of the conversations (first answer, resolution, each agent, templates paid each
    month) against the targets of the WhatsApp account."""

    _inherit = "ocd.live.dashboard"

    @api.model
    def get_dashboard_data(self):
        data = super().get_dashboard_data()
        data["whatsapp"] = self._ocd_whatsapp_stats(STATS_DAYS[0])
        return data

    @api.model
    def get_whatsapp_stats(self, days=STATS_DAYS[0]):
        """The figures of the conversations over another period (7 or 30 days)."""
        return self._ocd_whatsapp_stats(days if days in STATS_DAYS else STATS_DAYS[0])

    @api.model
    def _ocd_whatsapp_stats(self, days):
        """The figures of the conversations for the screen, each with its target and its tone
        (green: target met, yellow: beyond, red: beyond the delay that alerts the managers). For
        the WhatsApp agents; the figures of each agent for the managers only."""
        if not self.env.user.has_group("whatsapp_cloud.group_whatsapp_user"):
            return False
        accounts = self.env["whatsapp.account"].sudo().search([("company_id", "=", self.env.company.id)])
        if not accounts:
            return False
        _ = self.env._
        stats = accounts._whatsapp_stats(days)
        channel_model = self.env["discuss.channel"]

        def duration(minutes):
            # « 1 h 10 » never cut on two lines
            return channel_model._whatsapp_duration_text(minutes).replace(" ", "\u00a0")

        target, escalation = stats["first_answer_target"], stats["escalation_target"]

        def tone(minutes):
            if minutes is None or not target:
                return ""
            if minutes <= target:
                return "green"
            return "red" if escalation and minutes >= escalation else "yellow"

        answers, first = stats["answers"], stats["first_answer"]
        figures = [{
            "key": "first_answer",
            "label": _("First answer"),
            "value": duration(first) if first is not None else "–",
            "sub": (_("average of 1 answer") if answers == 1 else _("average of %s answers", answers))
            if answers else _("no answer in this period"),
            "target": _("target: within %s", duration(target)) if target else "",
            "tone": tone(first),
        }, {
            "key": "in_time",
            "label": _("Answered in time"),
            "value": f"{round(stats['in_time'] * 100 / answers)} %" if answers else "–",
            "sub": _("%(count)s of %(total)s answers within %(delay)s",
                     count=stats["in_time"], total=answers, delay=duration(target)) if answers and target else "",
            "target": "",
            "tone": "",
        }, {
            "key": "waiting",
            "label": _("Waiting now"),
            "value": str(stats["waiting"]),
            "sub": _("the oldest for %s", duration(stats["waiting_oldest"])) if stats["waiting"]
            else _("nobody is waiting"),
            "target": _("target: nobody"),
            "tone": "green" if not stats["waiting"] else tone(stats["waiting_oldest"]) or "yellow",
            "action": self._ocd_inbox_action(),
        }, {
            "key": "resolution",
            "label": _("Time to resolve"),
            "value": duration(stats["resolution"]) if stats["resolution"] is not None else "–",
            "sub": (_("average of 1 conversation") if stats["resolutions"] == 1
                    else _("average of %s conversations", stats["resolutions"])) if stats["resolutions"]
            else _("none resolved in this period"),
            "target": "",
            "tone": "",
        }]
        agents = []
        if self.env.user.has_group("whatsapp_cloud.group_whatsapp_manager"):
            agents = [{
                "key": row["user_id"],
                "name": row["name"],
                "conversations": row["conversations"],
                "first_answer": duration(row["first_answer"]) if row["first_answer"] is not None else "–",
                "tone": tone(row["first_answer"]),
                "resolved": row["resolved"],
            } for row in stats["agents"]]
        categories = {
            "marketing": _("marketing"), "utility": _("utility"), "authentication": _("authentication"),
            "service": _("service"),
        }
        top = max([row["sent"] for row in stats["templates"]] + [1])
        templates = [{
            "key": row["month"].isoformat(),
            "label": format_date(self.env, row["month"], date_format="MMM yyyy"),
            "sent": row["sent"],
            "paid": row["paid"],
            "value": _("%(sent)s · 1 paid", sent=row["sent"]) if row["paid"] == 1
            else _("%(sent)s · %(paid)s paid", sent=row["sent"], paid=row["paid"]),
            "width": round(row["sent"] / top * 100, 1),
            "paid_width": round(row["paid"] / top * 100, 1),
            "detail": " · ".join(
                f"{categories.get(key, key)} {count}" for key, count in sorted(row["categories"].items())
            ),
        } for row in stats["templates"]]
        return {
            "days": days,
            "periods": list(STATS_DAYS),
            "subtitle": _("Last %(days)s days · %(count)s conversations · opening hours of the account",
                          days=days, count=stats["conversations"]),
            "figures": figures,
            "agents": agents,
            "templates": templates,
            "templates_action": {
                "type": "ir.actions.act_window",
                "name": _("Templates sent"),
                "res_model": "whatsapp.message",
                "views": [[False, "list"], [False, "form"]],
                "domain": [("message_type", "=", "template"), ("direction", "=", "outgoing")],
            },
        }

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
            "action": self._ocd_inbox_action(),
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
                "action": self._ocd_inbox_action(channel),
            })
        return todos

    @api.model
    def _ocd_inbox_action(self, channel=None):
        """The conversations of OCD Live, on `channel` when given."""
        action = {"type": "ir.actions.client", "tag": "ocd_live_whatsapp.inbox", "name": self.env._("Conversations")}
        if channel:
            action["context"] = {"active_id": channel.id}
        return action
