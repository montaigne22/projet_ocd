import io
from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time
from PIL import Image

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes

from odoo.addons.ocd_live.tests.common import pending_payment
from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon


def png(color=(91, 45, 176)):
    data = io.BytesIO()
    Image.new("RGB", (40, 40), color).save(data, "PNG")
    return data.getvalue()


@tagged("post_install", "-at_install")
class TestOcdVote(HttpCase, OcdShopCommon):
    """OCD Vote (chantier 4, design OcdVote): paid votes for contests. Only the paid votes count,
    each one linked to its payment."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({
            "ocd_vote_price": 100, "ocd_vote_pack1_votes": 10, "ocd_vote_pack1_price": 900,
            "ocd_vote_pack2_votes": 50, "ocd_vote_pack2_price": 4000, "ocd_vote_organizer_share": 60,
            "ocd_vote_hide_hours": 2, "ocd_vote_pay_minutes": 10, "phone": "+237 690000000",
        })
        cls.cameroon = cls.env.ref("base.cm")
        cls.organizer = cls.env["res.partner"].create({
            "name": "Etoile Events", "phone": "+237 677112233", "ocd_vote_organizer": True, "country_id": cls.cameroon.id,
        })
        cls.Contest = cls.env["ocd.vote.contest"]
        cls.Vote = cls.env["ocd.vote"]
        cls.VoteClass = type(cls.Vote)
        cls.AlertClass = type(cls.env["ocd.vote.alert"])

    def _contest(self, **values):
        now = fields.Datetime.now()
        contest = self.Contest.create({
            "name": "Miss Douala 2026", "organizer_id": self.organizer.id, "country_id": self.cameroon.id,
            "date_open": now - timedelta(days=1), "date_close": now + timedelta(days=5), **values,
        })
        for name in ("Aicha Mbappe", "Grace Ndongo", "Linda Eko"):
            self.env["ocd.vote.candidate"].create({"contest_id": contest.id, "name": name,
                                                   "photo": BinaryBytes(png(), filename="photo.png")})
        return contest

    def _open(self, **values):
        contest = self._contest(**values)
        contest.action_ocd_send_to_check()
        contest.action_ocd_approve()
        return contest

    def _paid(self, candidate, votes, voter=None):
        """Votes paid: a payment of the team checked, the order confirmed by the payment."""
        vote = self.Vote._ocd_create(candidate, votes, voter or self.estelle)
        transaction = pending_payment(self, vote.order_id)
        transaction._set_done()
        transaction._post_process()
        return vote

    # === THE CONTEST === #

    def test_a_contest_its_candidates_its_prices(self):
        contest = self._contest()
        self.assertEqual(contest.slug, "miss-douala-2026")
        self.assertEqual(self._contest().slug, "miss-douala-2026-2", "Each contest has its own address")
        self.assertEqual(contest.candidate_ids.mapped("number"), [1, 2, 3], "Numbered in order")
        self.assertEqual([(pack.votes, pack.price) for pack in contest.pack_ids], [(10, 900), (50, 4000)])
        self.assertEqual((contest._ocd_price(1), contest._ocd_price(10), contest._ocd_price(25)), (100, 900, 2500))
        choices = contest._ocd_choices()
        self.assertEqual([choice["offered"] for choice in choices], [False, "1 offered", "10 offered"])
        self.assertEqual(contest.organizer_share, 60)
        # Checked by the team before it shows: a contest without candidates cannot open
        self.assertFalse(contest._ocd_public())
        empty = self.Contest.create({"name": "Vide", "country_id": self.cameroon.id, "date_open": contest.date_open,
                                     "date_close": contest.date_close})
        with self.assertRaisesRegex(UserError, "candidates"):
            empty.action_ocd_send_to_check()
        contest.action_ocd_send_to_check()
        self.assertEqual(contest.state, "to_check")
        contest.action_ocd_approve()
        self.assertTrue(contest._ocd_is_open())
        self.assertEqual(set(contest.candidate_ids.mapped("state")), {"approved"})
        # Once the votes open, the price, the packs and the end no longer change
        with self.assertRaisesRegex(UserError, "no longer change"):
            contest.vote_price = 50
        with self.assertRaisesRegex(UserError, "free votes"):
            empty.vote_price = 0
        # The numbers hidden the last hours (the order stays), shown with the results
        self.assertFalse(contest._ocd_hidden())
        self.assertTrue(contest._ocd_hidden(contest.date_close - timedelta(hours=1)))
        contest.hide_hours = 0
        self.assertFalse(contest._ocd_hidden(contest.date_close - timedelta(hours=1)))

    def test_only_the_paid_votes_count(self):
        contest = self._open()
        aicha, grace, linda = contest.candidate_ids
        told = []
        with patch.object(self.VoteClass, "_ocd_tell_paid", lambda votes: told.append(votes)):
            waiting = self.Vote._ocd_create(aicha, 10, self.estelle)
            self.assertEqual(waiting.state, "pending")
            self.assertEqual(waiting.order_id.amount_total, 900, "The price of the pack")
            self.assertEqual(aicha.vote_count, 0, "Not paid: not counted")
            vote = self._paid(aicha, 10)
            self.assertEqual((vote.state, aicha.vote_count), ("paid", 10))
            self.assertEqual(told, [vote])
            self._paid(grace, 25, self.herve)
            self._paid(grace, 1, self.herve)
        self.assertEqual((contest.vote_count, contest.voter_count, contest.payment_count), (36, 2, 3))
        self.assertEqual((contest.amount_total, contest.organizer_amount), (3500, 2100))
        ranking = contest._ocd_ranking()
        self.assertEqual([(row["candidate"], row["votes"], row["rank"]) for row in ranking],
                         [(grace, 26, 1), (aicha, 10, 2), (linda, 0, 3)])
        # A payment refunded removes its votes
        vote.action_ocd_refund()
        self.assertEqual((vote.state, aicha.vote_count), ("refunded", 0))
        # Not paid in time: cancelled with its order; a payment checked by the team keeps waiting
        checking = self.Vote._ocd_create(linda, 1, self.herve)
        pending_payment(self, checking.order_id)
        self.Vote._ocd_cancel_unpaid(fields.Datetime.now() + timedelta(minutes=11))
        self.assertEqual((waiting.state, waiting.order_id.state), ("cancelled", "cancel"))
        self.assertEqual(checking.state, "pending")
        with self.assertRaisesRegex(UserError, "between 1"):
            self.Vote._ocd_create(linda, 0, self.herve)
        # A payment started after the end does not count: to refund
        late = self.Vote._ocd_create(linda, 1, self.herve)
        contest.with_context(ocd_vote_force=True).date_close = fields.Datetime.now() - timedelta(minutes=1)
        transaction = pending_payment(self, late.order_id)
        transaction._set_done()
        transaction._post_process()
        self.assertEqual((late.state, linda.vote_count), ("late", 0))
        with self.assertRaisesRegex(UserError, "not open"):
            self.Vote._ocd_create(linda, 1, self.herve)

    def test_the_end_the_results_the_payout(self):
        contest = self._open()
        aicha = contest.candidate_ids[0]
        self._paid(aicha, 50)
        # The scheduled task closes the votes at the end
        with freeze_time(contest.date_close + timedelta(minutes=1)):
            self.Contest._cron_ocd_vote()
        self.assertEqual(contest.state, "closed")
        contest.payout_momo = "+237 677112233"
        contest.action_ocd_publish_results()
        self.assertEqual((contest.state, contest.payout_state), ("done", "to_pay"))
        self.assertEqual(contest.payout_due, fields.Date.today() + timedelta(days=3))
        self.assertEqual(contest._ocd_winner_text(), "N° 1 Aicha Mbappe")
        signature = contest._ocd_signature()
        self.assertEqual(len(signature), 16)
        self.assertEqual(contest._ocd_signature(), signature, "The same results, the same signature")
        with self.assertRaisesRegex(UserError, "reference"):
            contest.action_ocd_payout_paid()
        contest.payout_reference = "MOMO-123"
        contest.action_ocd_payout_paid()
        self.assertEqual(contest.payout_state, "paid")
        self.authenticate(None, None)
        page = self.url_open(f"/vote/{contest.slug}/resultats").text
        self.assertIn("Aicha Mbappe wins Miss Douala 2026", page)
        self.assertIn(signature, page)

    def test_the_final_tells_the_people_who_asked(self):
        contest = self._open(final_at=fields.Datetime.now() + timedelta(hours=2), final_url="https://www.tiktok.com/@etoile/live")
        self.authenticate(None, None)
        response = self.url_open(f"/vote/{contest.slug}/finale",
                                 data={"csrf_token": self.csrf_token(), "phone": "670000099", "country_id": self.cameroon.id})
        self.assertIn("prevenu=1", response.url)
        alert = self.env["ocd.vote.alert"].search([("contest_id", "=", contest.id)])
        self.assertEqual(alert.partner_id.phone, "+237 670000099")
        told = []
        with patch.object(self.AlertClass, "_ocd_tell_final", lambda alerts: told.append(alerts)):
            self.Contest._cron_ocd_vote()
            self.assertEqual(told, [], "Not yet")
            with freeze_time(contest.final_at - timedelta(minutes=5)):
                self.Contest._cron_ocd_vote()
                self.Contest._cron_ocd_vote()
        self.assertEqual(told, [alert], "Once")

    # === THE PAGES OF THE PUBLIC === #

    def test_the_pages_vote_and_pay(self):
        draft = self._contest(name="Pas encore")
        contest = self._open()
        aicha = contest.candidate_ids[0]
        self._paid(aicha, 10)
        self.authenticate(None, None)
        self.assertEqual(self.url_open(f"/vote/{draft.slug}").status_code, 404, "Not checked yet")
        page = self.url_open("/vote").text
        self.assertIn("Miss Douala 2026", page)
        self.assertNotIn("Pas encore", page)
        page = self.url_open(f"/vote/{contest.slug}").text
        for text in ("Aicha Mbappe", "Grace Ndongo", "10 votes", "VOTE and the number", "Live ranking"):
            self.assertIn(text, page)
        self.assertIn('href="/vote"', page, "« Votes » in the menu")
        page = self.url_open(f"/vote/{contest.slug}?q=grace").text
        self.assertIn("Grace Ndongo", page)
        self.assertNotIn("Linda Eko", page)
        self.assertIn("Linda Eko", self.url_open(f"/vote/{contest.slug}?q=3").text, "Found by her number")
        page = self.url_open(f"/vote/{contest.slug}/1").text
        self.assertIn("How many votes?", page)
        self.assertIn("1 offered", page)
        self.assertEqual(self.url_open(f"/vote/{contest.slug}/9").status_code, 404)
        # Vote: the number of a pack, the Mobile Money number, then the page of the payment
        response = self.url_open(f"/vote/{contest.slug}/1", data={
            "csrf_token": self.csrf_token(), "votes": "50", "phone": "670000123", "country_id": self.cameroon.id,
        })
        vote = self.Vote.search([("partner_id.phone", "=", "+237 670000123")])
        self.assertEqual((vote.votes, vote.amount_company, vote.state, vote.source), (50, 4000, "pending", "page"))
        self.assertIn(f"/vote/voix/{vote.id}", response.url)
        self.assertEqual(self.url_open(f"/vote/voix/{vote.id}?t=wrong").status_code, 404)
        provider = self.env.ref("ocd_live.payment_provider_momo_team")
        provider.write({"active": True, "available_country_ids": [fields.Command.link(self.cameroon.id)]})
        page = self.url_open(vote._ocd_page_path()).text
        self.assertIn(f'data-provider-id="{provider.id}"', page)
        self.assertIn(f"/vote/voix/{vote.id}", page, "The voter comes back to this page after paying")
        # Another number of votes, and a wrong number
        self.url_open(f"/vote/{contest.slug}/2", data={
            "csrf_token": self.csrf_token(), "votes": "autre", "autre": "25", "phone": "670000124",
            "country_id": self.cameroon.id,
        })
        self.assertEqual(self.Vote.search([("partner_id.phone", "=", "+237 670000124")]).amount_company, 2500)
        page = self.url_open(f"/vote/{contest.slug}/2", data={
            "csrf_token": self.csrf_token(), "votes": "1", "phone": "12", "country_id": self.cameroon.id,
        }).text
        self.assertIn("This number is not a number of", page)
        # Paid: counted, the receipt
        transaction = pending_payment(self, vote.order_id)
        page = self.url_open(vote._ocd_page_path()).text
        self.assertIn("I paid", page, "The team checks the Mobile Money")
        transaction._set_done()
        vote.order_id.action_confirm()  # what the processing of the payment does
        page = self.url_open(vote._ocd_page_path()).text
        self.assertIn("50 votes for Aicha Mbappe, it is counted", page)
        self.assertIn("now has 60 votes", page)
        self.assertIn("Receipt", page)
        # The ranking, the band of the final (its own address)
        self.assertIn("Aicha Mbappe", self.url_open(f"/vote/{contest.slug}/classement/liste").text)
        self.assertEqual(self.url_open(f"/vote/{contest.slug}/bandeau/wrong").status_code, 404)
        band = self.url_open(contest._ocd_band_path()).text
        self.assertIn("Vote now", band)
        self.assertIn("60", band)
        # The last hours: the order stays, the numbers are hidden
        with freeze_time(contest.date_close - timedelta(hours=1)):
            page = self.url_open(f"/vote/{contest.slug}/classement").text
        self.assertIn("the numbers are hidden", page)
        self.assertNotIn(">60<", page)
        # The photos of the candidates shown
        self.assertEqual(self.url_open(aicha._ocd_photo_url()).status_code, 200)
        self.assertEqual(self.url_open(draft.candidate_ids[0]._ocd_photo_url()).status_code, 404)

    # === THE ORGANISER === #

    def test_the_space_of_the_organiser(self):
        contest = self._contest()
        self.authenticate(None, None)
        self.assertIn("/vote/organisateur/connexion", self.url_open("/vote/organisateur").url)
        Partner = type(self.env["res.partner"])
        with patch.object(Partner, "_ocd_send_login_code", lambda partner: True), \
                patch.object(Partner, "_ocd_check_login_code", lambda partner, code: code == "123456"):
            page = self.url_open("/vote/organisateur/connexion", data={
                "csrf_token": self.csrf_token(), "phone": "677112233", "country_id": self.cameroon.id,
            }).text
            self.assertIn('name="code"', page)
            response = self.url_open("/vote/organisateur/code", data={"csrf_token": self.csrf_token(), "code": "123456"})
        self.assertIn(f"/vote/organisateur/concours/{contest.id}", response.url, "Their only contest")
        for text in ("Paid votes", "Your share (60 %)", "Send my contest to OCD Live", "The steps"):
            self.assertIn(text, response.text)
        # Their candidates: added with a photo, numbered in order
        response = self.url_open(f"/vote/organisateur/concours/{contest.id}/candidates", data={
            "csrf_token": self.csrf_token(), "name": "Sandrine Tchami", "city": "Bonaberi",
        }, files={"photo": ("photo.png", png(), "image/png")})
        self.assertIn("Added: N° 4.", response.text)
        sandrine = contest.candidate_ids.filtered(lambda candidate: candidate.name == "Sandrine Tchami")
        self.assertEqual((sandrine.number, sandrine.state), (4, "to_check"))
        response = self.url_open(f"/vote/organisateur/concours/{contest.id}/envoyer", data={"csrf_token": self.csrf_token()})
        self.assertEqual(contest.state, "to_check")
        self.assertIn("the team checks your contest", response.text)
        # The team checks it (« To check »): everything is shown
        Verification = self.env["ocd.live.verification"]
        items = next(column for column in Verification._ocd_columns() if column["key"] == "vote")["items"]
        self.assertEqual([item["kind"] for item in items], ["vote_contest"])
        Verification.ocd_approve("vote_contest", contest.id)
        self.assertEqual((contest.state, sandrine.state), ("approved", "approved"))
        # After the opening: a new photo waits for the team, the name no longer changes
        self.url_open(f"/vote/organisateur/candidate/{sandrine.id}", data={
            "csrf_token": self.csrf_token(), "name": "Autre nom", "bio": "22 ans, coiffeuse",
        }, files={"photo": ("photo.png", png((200, 0, 0)), "image/png")})
        self.assertEqual(sandrine.name, "Sandrine Tchami")
        self.assertTrue(sandrine.pending_photo)
        self.assertEqual(sandrine.pending_bio, "22 ans, coiffeuse")
        items = next(column for column in Verification._ocd_columns() if column["key"] == "vote")["items"]
        self.assertEqual([item["key"] for item in items], [f"vote_candidate_{sandrine.id}"])
        reason = self.env.ref("ocd_vote.refuse_reason_vote_photo")
        Verification.ocd_refuse("vote_candidate", sandrine.id, reason.id)
        self.assertEqual((sandrine.state, bool(sandrine.pending_photo)), ("approved", False), "Stays as she was")
        # Another organiser sees nothing of it
        self.assertEqual(self.url_open(f"/vote/organisateur/candidate/{contest.candidate_ids[0].id}").status_code, 200)
        other = self._contest(organizer_id=self.env["res.partner"].create({"name": "Autre", "ocd_vote_organizer": True}).id)
        self.assertEqual(self.url_open(f"/vote/organisateur/concours/{other.id}").status_code, 404)

    def test_the_back_office(self):
        contest = self._open()
        self.assertEqual(contest.action_ocd_view_votes()["domain"], [("contest_id", "=", contest.id)])
        self.assertIn(f"/vote/{contest.slug}/bandeau/", contest.action_ocd_open_band()["url"])
        sections = str(self.env["ocd.live.settings"]._ocd_sections())
        for text in ("Price of a vote", "First pack", "Share of the organiser", "Ranking hidden at the end"):
            self.assertIn(text, sections)
        page = self.env["ocd.automation"].get_automations_page()
        groups = [group["key"] for group in page["groups"]] if "groups" in page else str(page)
        self.assertIn("votes", str(groups))
        self.assertEqual(self.organizer.action_ocd_view_contests()["domain"], [("organizer_id", "=", self.organizer.id)])
        with self.assertRaisesRegex(UserError, "paid votes"):
            self._paid(contest.candidate_ids[0], 1)
            contest.action_ocd_cancel()
