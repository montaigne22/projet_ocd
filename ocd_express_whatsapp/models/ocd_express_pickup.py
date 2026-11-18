from odoo import models


class OcdExpressPickup(models.Model):
    _inherit = "ocd.express.pickup"

    def _ocd_notify_done(self, taken):
        """Override of `ocd_express`: the sender receives the parcels taken, and reports a courier
        who is not the one of the message."""
        super()._ocd_notify_done(taken)
        self.env["res.partner"]._ocd_whatsapp_send("ocd_express_whatsapp.template_express_picked", self)

    def _ocd_taken_text(self):
        """« EX-0427, EX-0428 and EX-0429 »."""
        self.ensure_one()
        names = self.parcel_ids.filtered(lambda p: p.ocd_picked_at).sorted("id").mapped("name")
        if len(names) <= 1:
            return names[0] if names else ""
        return self.env._("%(first)s and %(last)s", first=", ".join(names[:-1]), last=names[-1])

    def _ocd_count_text(self):
        count = self.taken_count
        return self.env._("%s parcels", count) if count != 1 else self.env._("1 parcel")

    def _ocd_hour_text(self):
        self.ensure_one()
        return self.company_id._ocd_to_local(self.done_at).strftime("%H:%M") if self.done_at else ""
