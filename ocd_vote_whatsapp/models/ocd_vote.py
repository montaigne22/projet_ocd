from odoo import models


class OcdVote(models.Model):
    _inherit = "ocd.vote"

    def _ocd_tell_paid(self):
        """Override of `ocd_vote`: the voter just paid, the message tells their votes are counted
        (ocd_vote_comptee); never after STOP."""
        super()._ocd_tell_paid()
        Partner = self.env["res.partner"]
        for vote in self.sudo().filtered(lambda vote: not vote.partner_id.whatsapp_opt_out):
            Partner._ocd_whatsapp_send("ocd_vote_whatsapp.template_vote_counted", vote, requested=True)


class OcdVoteAlert(models.Model):
    _inherit = "ocd.vote.alert"

    def _ocd_tell_final(self):
        """Override of `ocd_vote`: « the final starts », to the people who asked (ocd_vote_finale)."""
        super()._ocd_tell_final()
        alerts = self.sudo().filtered(lambda alert: not alert.partner_id.whatsapp_opt_out)
        if alerts:
            self.env["res.partner"]._ocd_whatsapp_send("ocd_vote_whatsapp.template_vote_final", alerts, requested=True)
