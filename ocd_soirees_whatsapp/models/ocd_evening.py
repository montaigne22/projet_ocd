from odoo import models


class OcdEvening(models.Model):
    _inherit = "ocd.evening"

    def _ocd_tell_invited(self, vendors):
        """Override of `ocd_soirees`: the invitation of the vendors (ocd_soiree_invitation), in the
        language of each vendor; never after STOP."""
        super()._ocd_tell_invited(vendors)
        Partner = self.env["res.partner"]
        for evening in self:
            for vendor in vendors.sudo().filtered(lambda vendor: not vendor.whatsapp_opt_out):
                local = evening.with_context(lang=vendor.lang or self.env.lang)
                tz_name = vendor._ocd_tz_name()
                Partner._ocd_whatsapp_send(
                    "ocd_soirees_whatsapp.template_evening_invite", vendor,
                    ocd_evening_name=evening.name,
                    ocd_evening_when=local._ocd_when_sentence(tz_name),
                    ocd_evening_until=local._ocd_registration_day(tz_name),
                    ocd_evening_path=f"ocd/espace/moi/evenements/{evening.id}",
                )

    def _ocd_tell_alerts(self):
        """Override of `ocd_soirees`: « the event starts » (ocd_soiree_commence), to the people
        who asked; never after STOP."""
        super()._ocd_tell_alerts()
        alerts = self.sudo().alert_ids.filtered(lambda alert: not alert.partner_id.whatsapp_opt_out)
        if alerts:
            self.env["res.partner"]._ocd_whatsapp_send("ocd_soirees_whatsapp.template_evening_start", alerts,
                                                        requested=True)


class OcdEveningAlert(models.Model):
    _inherit = "ocd.evening.alert"

    def _ocd_whatsapp_hour(self, value):
        """An hour of the event at the hour of the person told."""
        self.ensure_one()
        evening = self.evening_id
        return evening._ocd_hour(evening._ocd_local(value, self.partner_id._ocd_tz_name()))

    def _ocd_whatsapp_until(self):
        """The end of the event at the hour of the person told: « 23:00 », or « Sunday 7 December
        at 23:00 » for several days."""
        self.ensure_one()
        return self.evening_id._ocd_until_text(self.partner_id._ocd_tz_name())
