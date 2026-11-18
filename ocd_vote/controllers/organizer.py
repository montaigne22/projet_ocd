"""The space of an organiser of contests (design OcdVote): they log in with their number like the
vendors (a code on WhatsApp), see their contest (votes, money collected, their share, the steps),
share it, open the band of the final and manage their candidates."""
import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import BinaryBytes, consteq

from odoo.addons.ocd_live import page_cache, tools
from odoo.addons.ocd_live.controllers import common
from odoo.addons.ocd_live_shop.controllers.member_space import OcdMemberLogin
from odoo.addons.ocd_live_shop.controllers.vendor_products import read_photo

_logger = logging.getLogger(__name__)

SESSION_ORGANIZER = "ocd_organizer_id"
SESSION_ORGANIZER_TOKEN = "ocd_organizer_token"
ORGANIZER_COOKIE = "ocd_organizer"
HOME = "/vote/organisateur"
LOGIN = "/vote/organisateur/connexion"
NAME_MAX = 60

page_cache.PERSONAL_COOKIES.add(ORGANIZER_COOKIE)


def current_organizer():
    """The organiser opened on this browser (a code checked), as long as their personal secret is
    the same and they are still an organiser."""
    Partner = request.env["res.partner"].sudo()
    partner_id = request.session.get(SESSION_ORGANIZER)
    if not partner_id:
        partner = common.browser_partner(ORGANIZER_COOKIE, "organizer")
        if partner and partner.ocd_vote_organizer:
            _logger.info("OCD Vote: organiser %s opened again by the cookie of the browser", partner.id)
            remember_organizer(partner)
            return partner
        return Partner
    partner = Partner.browse(partner_id).exists()
    token = request.session.get(SESSION_ORGANIZER_TOKEN) or ""
    if partner.ocd_vote_organizer and partner.ocd_space_token and consteq(partner.ocd_space_token, token):
        return partner
    forget_organizer()
    return Partner


def remember_organizer(partner):
    request.session[SESSION_ORGANIZER] = partner.id
    request.session[SESSION_ORGANIZER_TOKEN] = partner._ocd_get_space_token()
    common.remember_browser(ORGANIZER_COOKIE, partner, "organizer")


def forget_organizer():
    request.session.pop(SESSION_ORGANIZER, None)
    request.session.pop(SESSION_ORGANIZER_TOKEN, None)
    common.forget_browser(ORGANIZER_COOKIE)


class OcdVoteOrganizerLogin(OcdMemberLogin):
    """The login of the organisers: their number, then a code on WhatsApp (no link of their own:
    no message to approve at Meta for them)."""

    LOGIN_PAGES = dict(OcdMemberLogin.LOGIN_PAGES, vote={"form": LOGIN, "code": "/vote/organisateur/code", "home": HOME})

    def _login_page_mode(self, target):
        if target == "vote":
            return "whatsapp_code"
        return super()._login_page_mode(target)

    def _ocd_login_partner(self, number, target):
        if target == "vote":
            return request.env["res.partner"].sudo()._ocd_find_organizer_by_phone(number)
        return super()._ocd_login_partner(number, target)

    def _ocd_open_session(self, partner, target):
        if target == "vote":
            remember_organizer(partner)
            return HOME
        return super()._ocd_open_session(partner, target)

    @http.route(LOGIN, type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def organizer_login(self, **kwargs):
        if current_organizer():
            return request.redirect(HOME)
        if request.env.user._is_internal():
            return self._render_team()
        return self._render_login(target="vote")

    @http.route(LOGIN, type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def organizer_login_phone(self, phone=None, country_id=None, **kwargs):
        return self._login_phone(phone, country_id, "vote")

    @http.route("/vote/organisateur/code", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def organizer_login_code(self, code=None, **kwargs):
        return self._login_code(code, "vote")

    @http.route("/vote/organisateur/deconnexion", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def organizer_logout(self, **kwargs):
        forget_organizer()
        return request.redirect(LOGIN)


class OcdVoteOrganizer(http.Controller):

    def _organizer(self):
        return current_organizer()

    def _contest(self, organizer, contest_id):
        contest = request.env["ocd.vote.contest"].sudo().browse(contest_id).exists()
        if not contest or contest.organizer_id != organizer:
            raise request.not_found()
        return contest

    def _page(self, template, **values):
        return request.render(template, common.page_values(
            False,
            nav="votes",
            header_link={"href": "/vote/organisateur/deconnexion", "post": True, "label": request.env._("Log out")},
            **values,
        ))

    @http.route(HOME, type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def home(self, **kwargs):
        organizer = self._organizer()
        if not organizer:
            return request.redirect(LOGIN)
        contests = organizer.ocd_vote_contest_ids.filtered(lambda contest: contest.state != "cancelled")
        if len(contests) == 1:
            return request.redirect(f"/vote/organisateur/concours/{contests.id}")
        return self._page("ocd_vote.organizer_home", back="/vote", header_title=request.env._("My contests"),
                          organizer=organizer, contests=contests)

    def _steps(self, contest):
        env = request.env
        now = common.now()
        candidates = contest.candidate_ids.filtered(lambda candidate: candidate.state != "refused")
        local_open = contest._ocd_local(contest.date_open)
        steps = [
            (contest.state != "draft", env._("Contest and rules sent")),
            (contest.state in ("approved", "closed", "done"), env._("Checked by OCD Live (organiser and rules)")),
            (bool(candidates) and not candidates.filtered(lambda c: c.state == "to_check" or not c.photo),
             env._("%s candidates, each with a photo and a number", len(candidates))),
            (contest.state in ("approved", "closed", "done") and now >= contest.date_open,
             env._("Votes open on %s", tools_day(contest, local_open))),
            (contest.state == "done", env._("End on %s, then the certified results", contest._ocd_close_text())),
            (contest.payout_state == "paid",
             env._("Your share paid within 3 days on your Mobile Money") if contest.payout_state != "paid"
             else env._("Your share paid: %s", contest.payout_reference or "-")),
        ]
        return [{"done": done, "label": label, "index": index + 1} for index, (done, label) in enumerate(steps)]

    @http.route("/vote/organisateur/concours/<int:contest_id>", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def contest(self, contest_id, envoye=None, **kwargs):
        organizer = self._organizer()
        if not organizer:
            return request.redirect(LOGIN)
        contest = self._contest(organizer, contest_id)
        env = request.env
        today_votes = sum(contest.vote_ids.filtered(
            lambda vote: vote.state == "paid" and vote.paid_at and vote.paid_at.date() == common.now().date()
        ).mapped("votes"))
        return self._page(
            "ocd_vote.organizer_contest",
            back=HOME if len(organizer.ocd_vote_contest_ids) > 1 else "/vote",
            header_title=env._("My contest"),
            contest=contest,
            steps=self._steps(contest),
            tiles=[
                (env._("Paid votes"), contest._ocd_number(contest.vote_count),
                 env._("1 person") if contest.voter_count == 1 else env._("%s people", contest._ocd_number(contest.voter_count))),
                (env._("Collected"), contest._ocd_money(contest.amount_total), env._("with the packs")),
                (env._("Your share (%s %%)", round(contest.organizer_share)), contest._ocd_money(contest.organizer_amount),
                 env._("after the votes")),
                (env._("Today"), f"+{contest._ocd_number(today_votes)}", env._("votes")),
            ],
            state_label=dict(contest._fields["state"]._description_selection(env))[contest.state]
            if not contest._ocd_is_open() else env._("Votes open"),
            candidates_label=env._("The candidates · %s", len(contest.candidate_ids.filtered(
                lambda candidate: candidate.state != "refused"))),
            share_url=request.httprequest.url_root.rstrip("/") + f"/vote/{contest.slug}",
            band_url=contest._ocd_band_path(),
            message=env._("Sent: the team checks your contest and writes to you on WhatsApp.") if envoye else None,
        )

    @http.route("/vote/organisateur/concours/<int:contest_id>/envoyer", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def send(self, contest_id, **post):
        organizer = self._organizer()
        if not organizer:
            return request.redirect(LOGIN)
        contest = self._contest(organizer, contest_id)
        try:
            contest.action_ocd_send_to_check()
        except UserError:
            return request.redirect(f"/vote/organisateur/concours/{contest.id}/candidates")
        return request.redirect(f"/vote/organisateur/concours/{contest.id}?envoye=1")

    # === THE CANDIDATES === #

    def _render_candidates(self, organizer, contest, error=None, values=None, added=False):
        env = request.env
        candidates = contest.candidate_ids.sorted("number")
        counts = candidates._ocd_vote_counts()
        ranking = {row["candidate"].id: row["rank"] for row in contest._ocd_ranking()}
        rows = []
        for candidate in candidates:
            if candidate.state == "refused":
                line = env._("Refused: %s", candidate.refuse_reason or "-")
            elif candidate.state == "to_check":
                line = env._("To check by OCD Live")
            elif candidate.has_pending:
                line = env._("Change to check by OCD Live")
            elif not candidate.photo:
                line = env._("Add the photo")
            else:
                votes = counts.get(candidate.id, 0)
                line = " · ".join([
                    env._("1 vote") if votes == 1 else env._("%s votes", contest._ocd_number(votes)),
                    contest._ocd_rank_label(ranking[candidate.id]) if votes and candidate.id in ranking else "",
                ]).strip(" ·")
            rows.append({"candidate": candidate, "line": line,
                         "photo": f"/vote/organisateur/photo/{candidate.id}" if candidate.photo else False})
        last = candidates[-1:].number or 0
        return self._page(
            "ocd_vote.organizer_candidates",
            back=f"/vote/organisateur/concours/{contest.id}",
            header_title=env._("The candidates"),
            contest=contest,
            rows=rows,
            add_hint=env._(
                "The number is given in order (the next one: %s). A candidate added or changed after the opening is "
                "checked by the team before being shown. A candidate who has votes is not removed: the team decides "
                "with you.", last + 1),
            can_add=contest.state in ("draft", "to_check", "approved"),
            values=values or {},
            error=error,
            message=env._("Added: N° %s.", added) if added else None,
        )

    @http.route("/vote/organisateur/concours/<int:contest_id>/candidates", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def candidates(self, contest_id, ajoute=None, **kwargs):
        organizer = self._organizer()
        if not organizer:
            return request.redirect(LOGIN)
        contest = self._contest(organizer, contest_id)
        return self._render_candidates(organizer, contest, added=ajoute)

    def _read_values(self, post, photo, required_photo):
        env = request.env
        values = {
            "name": common.clean_text(post.get("name"), NAME_MAX),
            "bio": common.clean_text(post.get("bio"), 200),
            "city": common.clean_text(post.get("city"), 60),
        }
        data, filename, error = read_photo(photo, env._("Add the photo."))
        if error:
            raise UserError(error)
        if data:
            values["photo"] = BinaryBytes(data, filename=filename)
        if not values["name"]:
            raise UserError(env._("Write the name."))
        if required_photo and not data:
            raise UserError(env._("Add the photo."))
        return values

    @http.route("/vote/organisateur/concours/<int:contest_id>/candidates", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def candidate_add(self, contest_id, photo=None, **post):
        organizer = self._organizer()
        if not organizer:
            return request.redirect(LOGIN)
        contest = self._contest(organizer, contest_id)
        try:
            if contest.state not in ("draft", "to_check", "approved"):
                raise UserError(request.env._("The votes are closed: no new candidate."))
            values = self._read_values(post, photo, required_photo=True)
            candidate = request.env["ocd.vote.candidate"].sudo().create({
                **values, "contest_id": contest.id, "state": "to_check",
            })
        except UserError as exc:
            return self._render_candidates(organizer, contest, error=exc.args[0], values=post)
        return request.redirect(f"/vote/organisateur/concours/{contest.id}/candidates?ajoute={candidate.number}")

    def _own_candidate(self, organizer, candidate_id):
        candidate = request.env["ocd.vote.candidate"].sudo().browse(candidate_id).exists()
        if not candidate or candidate.contest_id.organizer_id != organizer:
            raise request.not_found()
        return candidate

    @http.route("/vote/organisateur/candidate/<int:candidate_id>", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def candidate_page(self, candidate_id, **kwargs):
        organizer = self._organizer()
        if not organizer:
            return request.redirect(LOGIN)
        candidate = self._own_candidate(organizer, candidate_id)
        return self._render_candidate(candidate)

    def _render_candidate(self, candidate, error=None):
        contest = candidate.contest_id
        return self._page(
            "ocd_vote.organizer_candidate",
            back=f"/vote/organisateur/concours/{contest.id}/candidates",
            header_title=candidate._ocd_label(),
            contest=contest,
            candidate=candidate,
            locked_name=contest.state not in ("draft", "to_check") and candidate.state == "approved",
            photo=f"/vote/organisateur/photo/{candidate.id}" if candidate.photo else False,
            error=error,
        )

    @http.route("/vote/organisateur/candidate/<int:candidate_id>", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def candidate_change(self, candidate_id, photo=None, **post):
        organizer = self._organizer()
        if not organizer:
            return request.redirect(LOGIN)
        candidate = self._own_candidate(organizer, candidate_id)
        try:
            if "name" not in post:
                post = dict(post, name=candidate.name)
            candidate._ocd_organizer_change(self._read_values(post, photo, required_photo=False))
        except UserError as exc:
            return self._render_candidate(candidate, error=exc.args[0])
        return request.redirect(f"/vote/organisateur/concours/{candidate.contest_id.id}/candidates")

    @http.route("/vote/organisateur/photo/<int:candidate_id>", type="http", auth="public", website=True, sitemap=False)
    def candidate_photo(self, candidate_id, **kwargs):
        organizer = self._organizer()
        if not organizer:
            raise request.not_found()
        candidate = self._own_candidate(organizer, candidate_id)
        field = "pending_photo" if candidate.pending_photo else "photo"
        stream = request.env["ir.binary"]._get_image_stream_from(candidate, field, width=256, height=256)
        return stream.get_response()


def tools_day(contest, local):
    return tools.day_text(request.env, local.date(), "d MMM")


def _is_known_organizer():
    return "ocd.vote.contest" in request.env and bool(current_organizer())


# The organiser changes page without reloading it, as the vendors
common.FAST_NAVIGATION_CHECKS.append(_is_known_organizer)
