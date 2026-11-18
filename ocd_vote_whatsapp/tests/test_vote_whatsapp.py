from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.ocd_live.tests.common import pending_payment
from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdVoteWhatsapp(OcdShopCommon):
    """OCD Vote on WhatsApp (chantier 4, design OcdVote): « VOTE 12 », the votes counted, the final."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env["base"].with_context(lang="en_US").env
        cls.env["whatsapp.account"].search([]).active = False
        cls.account = cls.env["whatsapp.account"].create({
            "name": "OCD Live", "phone_number_id": "1110019", "waba_id": "2220019", "access_token": "test-token",
            "resource_calendar_id": False, "bot_enabled": True,
        })
        cls.company.write({"ocd_vote_price": 100, "ocd_vote_pack1_votes": 10, "ocd_vote_pack1_price": 900,
                           "ocd_vote_pack2_votes": 50, "ocd_vote_pack2_price": 4000})
        now = fields.Datetime.now()
        cls.contest = cls.env["ocd.vote.contest"].create({
            "name": "Miss Douala 2026", "country_id": cls.env.ref("base.cm").id,
            "date_open": now - timedelta(days=1), "date_close": now + timedelta(days=3),
            "final_at": now + timedelta(hours=1),
        })
        for name in ("Aicha Mbappe", "Grace Ndongo"):
            cls.env["ocd.vote.candidate"].create({"contest_id": cls.contest.id, "name": name})
        cls.contest.action_ocd_approve()
        cls.grace = cls.contest.candidate_ids[1]
        cls.voter = cls.env["res.partner"].create({
            "name": "Paul", "phone": "+237 670000039", "country_id": cls.env.ref("base.cm").id, "lang": "en_US",
        })
        cls.Message = cls.env["whatsapp.message"]

    def receive(self, body, wa_id, reply_id=None):
        message = {"from": "237670000039", "id": wa_id, "timestamp": "1760000000"}
        if reply_id:
            message.update(type="interactive", interactive={"type": "button_reply", "button_reply": {"id": reply_id, "title": body}})
        else:
            message.update(type="text", text={"body": body})
        return self.Message._process_incoming(self.account, message, [{"profile": {"name": "Paul"}, "wa_id": "237670000039"}])

    def sent(self, channel):
        return self.Message.search([("channel_id", "=", channel.id), ("direction", "=", "outgoing")], order="id")

    def test_vote_on_whatsapp(self):
        channel = self.receive("Vote n° 2", "wamid.V1").channel_id
        question = self.sent(channel)[-1:]
        self.assertIn("Miss Douala 2026 · N° 2 Grace Ndongo", question.body)
        self.assertIn("How many votes?", question.body)
        self.assertEqual(question.message_type, "interactive")
        self.assertIn("ocd_vote_pack_10", question.payload)
        self.receive("10 votes", "wamid.V2", reply_id="ocd_vote_pack_10")
        vote = self.env["ocd.vote"].search([("candidate_id", "=", self.grace.id)])
        self.assertEqual((vote.votes, vote.amount_company, vote.source, vote.state), (10, 900, "whatsapp", "pending"))
        self.assertEqual(vote.partner_id.phone and vote.partner_id.phone[-9:], "670000039")
        # No Mobile Money provider for this number: the link of the page of the payment
        answer = self.sent(channel).filtered(lambda message: "/vote/voix/" in (message.body or ""))
        self.assertTrue(answer, self.sent(channel).mapped("body"))
        self.assertIn(vote._ocd_page_path(), answer.body)
        # A number no contest open has
        self.receive("VOTE 99", "wamid.V3")
        self.assertIn("No open contest has the number 99", self.sent(channel)[-1:].body)

    def test_the_votes_counted_and_the_final(self):
        vote = self.env["ocd.vote"]._ocd_create(self.grace, 10, self.voter)
        transaction = pending_payment(self, vote.order_id)
        transaction._set_done()
        transaction._post_process()
        self.assertEqual(vote.state, "paid")
        messages = self.Message.search([("model", "=", "ocd.vote"), ("res_id", "=", vote.id)])
        self.assertEqual(messages.template_id.template_name, "ocd_vote_comptee")
        self.assertIn("10 votes for N° 2 Grace Ndongo in the contest Miss Douala 2026", messages.body)
        self.assertFalse(self.Message.search([
            ("model", "=", "sale.order"), ("res_id", "=", vote.order_id.id),
            ("template_id.template_name", "in", ("order_confirmed", "order_received")),
        ]), "Not the messages of the orders of the shop")
        template = self.env.ref("ocd_vote_whatsapp.template_vote_counted")
        self.assertEqual(template._render(template.button_url_value, vote)[vote.id], "vote/miss-douala-2026/classement")
        # The final: to the people who asked
        alert = self.env["ocd.vote.alert"].create({"contest_id": self.contest.id, "partner_id": self.voter.id})
        self.env["ocd.vote.contest"]._cron_ocd_vote()
        self.assertFalse(self.Message.search([("model", "=", "ocd.vote.alert")]), "Not yet")
        self.contest.final_at = fields.Datetime.now() + timedelta(minutes=5)
        self.env["ocd.vote.contest"]._cron_ocd_vote()
        final = self.Message.search([("model", "=", "ocd.vote.alert"), ("res_id", "=", alert.id)])
        self.assertEqual(final.template_id.template_name, "ocd_vote_finale")
