from babel.dates import get_day_names

from odoo import models
from odoo.tools.misc import format_duration, get_lang


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    def _whatsapp_get_address(self):
        self.ensure_one()
        partner = self.partner_id
        return ", ".join(filter(None, [partner.street, partner.street2, partner.city]))

    def _whatsapp_get_opening_hours(self):
        """Opening hours of the store (its "Opening Hours" schedule of Click & Collect), as
        lines grouping the days with the same hours: "Monday – Saturday: 09:00 – 19:00"."""
        self.ensure_one()
        calendar = self.opening_hours if "opening_hours" in self._fields else False
        if not calendar:
            return []
        intervals = {day: [] for day in range(7)}
        for attendance in calendar.attendance_ids.sorted("hour_from"):
            if attendance.hour_to <= attendance.hour_from:
                continue  # hours per day without times: no opening hours to show
            day = intervals[int(attendance.dayofweek)]
            if day and day[-1][1] == attendance.hour_from:
                day[-1][1] = attendance.hour_to
            else:
                day.append([attendance.hour_from, attendance.hour_to])
        if not any(intervals.values()):
            return []
        _ = self.env._
        day_names = get_day_names("wide", locale=get_lang(self.env).code)
        lines, start = [], 0
        for day in range(7):
            if day < 6 and intervals[day + 1] == intervals[day]:
                continue
            days = day_names[start].capitalize()
            if day != start:
                days = _("%(first)s – %(last)s", first=days, last=day_names[day])
            hours = ", ".join(
                f"{format_duration(begin)} – {format_duration(end)}" for begin, end in intervals[day]
            ) or _("closed")
            lines.append(_("%(days)s: %(hours)s", days=days, hours=hours))
            start = day + 1
        return lines
