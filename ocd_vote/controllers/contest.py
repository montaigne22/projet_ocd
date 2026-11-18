import unicodedata

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common
from odoo.addons.ocd_live.controllers.payment import OcdLivePayment
from odoo.addons.ocd_live_shop.controllers.vendor_follow import visitor_partner


def simple(text):
    """Without accents nor case: « Aïcha » is found by « aicha »."""
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower().strip()


def contest_or_404(slug, public=True):
    contest = request.env["ocd.vote.contest"].sudo().search([("slug", "=", slug)], limit=1)
    if not contest or (public and not contest._ocd_public()):
        raise request.not_found()
    return contest


def candidate_row(contest, row, hidden):
    """What a card of a candidate shows: her number, her rank, her votes (unless hidden)."""
    candidate = row["candidate"]
    return {
        "candidate": candidate,
        "rank": row["rank"],
        "rank_label": contest._ocd_rank_label(row["rank"]) if row["votes"] and row["rank"] <= 3 else False,
        "votes": row["votes"],
        "votes_text": False if hidden else (request.env._("1 vote") if row["votes"] == 1 else request.env._(
            "%s votes", contest._ocd_number(row["votes"]))),
        "number_text": contest._ocd_number(row["votes"]),
        "width": row["width"],
        "photo": candidate._ocd_photo_url(),
        "url": candidate._ocd_public_path(),
    }


def ranking_rows(contest):
    hidden = contest._ocd_hidden()
    return [candidate_row(contest, row, hidden) for row in contest._ocd_ranking()], hidden


class OcdVotePages(http.Controller):
    """The pages of OCD Vote for the public (design OcdVote): the contest, a candidate and her
    votes, the page of the payment and of the votes counted, the live ranking, the band of the
    final for the live, the results."""

    # === THE CONTESTS === #

    @http.route("/vote", type="http", auth="public", website=True, sitemap=True, ocd_cache=30)
    def contests(self, **kwargs):
        Contest = request.env["ocd.vote.contest"].sudo()
        contests = Contest.search([("state", "in", ("approved", "closed", "done"))], order="date_close desc", limit=40)
        now = common.now()
        rows = [{
            "contest": contest,
            "open": contest._ocd_is_open(now),
            "line": self._state_line(contest, now),
        } for contest in contests]
        rows.sort(key=lambda row: (not row["open"], row["contest"].date_close))
        return request.render("ocd_vote.contests", common.page_values(
            False, nav="votes", header_title=request.env._("Votes"), rows=rows,
        ))

    def _state_line(self, contest, now):
        env = request.env
        if contest._ocd_is_open(now):
            return env._("The votes close %s", contest._ocd_close_text())
        if contest.state == "approved" and now < contest.date_open:
            local = contest._ocd_local(contest.date_open)
            return env._("The votes open %(day)s at %(hour)s", day=tools.day_text(env, local.date(), "EEEE d MMMM"),
                         hour=contest._ocd_hour(local))
        if contest.state == "done":
            return env._("Results: %s", contest._ocd_winner_text() or "-")
        return env._("The votes are closed: the results come soon.")

    def _contest_values(self, contest):
        env = request.env
        now = common.now()
        rows, hidden = ranking_rows(contest)
        company = common.company()
        number = company.phone or ""
        return {
            "contest": contest,
            "open": contest._ocd_is_open(now),
            "hidden": hidden,
            "state_line": self._state_line(contest, now),
            "votes_total": contest._ocd_number(contest.vote_count),
            "candidates_total": len(rows),
            "left": contest._ocd_left_text(now) if contest._ocd_is_open(now) else False,
            "banner": f"/vote/image/{contest.id}?v={contest.write_date:%Y%m%d%H%M%S}" if contest.image else False,
            "how": env._(
                "Choose your candidate, then the number of votes: %(price)s a vote, paid with Mobile Money. Or on "
                "WhatsApp: write VOTE and the number to %(number)s.",
                price=contest._ocd_money(contest.vote_price), number=number,
            ) if number else env._(
                "Choose your candidate, then the number of votes: %s a vote, paid with Mobile Money.",
                contest._ocd_money(contest.vote_price),
            ),
            "organizer_line": env._("By %s", contest.organizer_id.name) if contest.organizer_id else env._("By OCD Live"),
            "report_url": tools.whatsapp_url(number, env._("Hello, I report the contest %s on OCD Live.", contest.name)),
            "final_line": env._("The final live on %(day)s at %(hour)s. The votes stay open until %(close)s.",
                                day=tools.day_text(env, contest._ocd_local(contest.final_at).date(), "EEE d MMM"),
                                hour=contest._ocd_hour(contest._ocd_local(contest.final_at)),
                                close=contest._ocd_hour(contest._ocd_local(contest.date_close)))
            if contest.final_at else False,
        }

    @http.route("/vote/<string:slug>", type="http", auth="public", website=True, sitemap=False, ocd_cache=10,
                ocd_cache_params=("vue", "q"))
    def contest(self, slug, vue=None, q=None, prevenu=None, **kwargs):
        contest = contest_or_404(slug)
        values = self._contest_values(contest)
        rows, hidden = ranking_rows(contest)
        if vue == "numeros":
            rows = sorted(rows, key=lambda row: row["candidate"].number)
        search = (q or "").strip()[:60]
        if search:
            digits = search.lstrip("#nN°º ").strip()
            words = simple(search)
            rows = [row for row in rows if (digits.isdigit() and row["candidate"].number == int(digits))
                    or (words and words in simple(row["candidate"].name))]
        return request.render("ocd_vote.contest", common.page_values(
            False,
            nav="votes",
            back="/vote",
            header_title=request.env._("Contest"),
            header_share=request.httprequest.url_root.rstrip("/") + f"/vote/{contest.slug}",
            rows=rows,
            view="numbers" if vue == "numeros" else "ranking",
            search=search,
            alert_noted=bool(prevenu),
            dial_rows=common.dial_rows(common.default_country()),
            **values,
        ))

    @http.route("/vote/<string:slug>/reglement", type="http", auth="public", website=True, sitemap=False, ocd_cache=60)
    def rules(self, slug, **kwargs):
        contest = contest_or_404(slug)
        return request.render("ocd_vote.rules", common.page_values(
            False, nav="votes", back=f"/vote/{contest.slug}", header_title=request.env._("Rules"),
            **self._contest_values(contest),
        ))

    # === A CANDIDATE: HER VOTES === #

    def _candidate(self, contest, number):
        candidate = contest.candidate_ids.filtered(lambda candidate: candidate.number == number and candidate._ocd_shown())
        if not candidate:
            raise request.not_found()
        return candidate

    @http.route("/vote/<string:slug>/<int:number>", type="http", auth="public", website=True, sitemap=False,
                methods=["GET"], ocd_cache=10)
    def candidate(self, slug, number, **kwargs):
        contest = contest_or_404(slug)
        return self._render_candidate(contest, self._candidate(contest, number))

    def _render_candidate(self, contest, candidate, error=None, values=None):
        env = request.env
        rows, hidden = ranking_rows(contest)
        row = next(row for row in rows if row["candidate"] == candidate)
        values = values or {}
        partner = visitor_partner()
        country = env["res.country"].sudo().browse(int(values.get("country_id") or 0)).exists() \
            or (partner.country_id if partner else None) or contest.country_id or common.default_country()
        phone = values.get("phone")
        if phone is None and partner and partner.phone:
            phone = common.local_digits(country, partner.phone) if common.normalize_phone(country, partner.phone) else ""
        choices = contest._ocd_choices()
        chosen = int(values["votes"]) if str(values.get("votes") or "").isdigit() else (
            choices[1]["votes"] if len(choices) > 1 else 1)
        if values.get("votes") == "autre":
            chosen = 0
        return request.render("ocd_vote.candidate", common.page_values(
            False,
            nav="votes",
            back=f"/vote/{contest.slug}",
            header_title=contest.name,
            header_share=request.httprequest.url_root.rstrip("/") + candidate._ocd_public_path(),
            contest=contest,
            candidate=candidate,
            row=row,
            hidden=hidden,
            open=contest._ocd_is_open(),
            state_line=self._state_line(contest, common.now()),
            choices=choices,
            chosen=chosen,
            other=values.get("autre") or 25,
            price_text=contest._ocd_money(contest.vote_price),
            dial_rows=common.dial_rows(country),
            phone_value=phone or "",
            error=error,
            pay_label=env._("Pay"),
        ))

    @http.route("/vote/<string:slug>/<int:number>", type="http", auth="public", website=True, sitemap=False,
                methods=["POST"])
    def candidate_vote(self, slug, number, votes=None, autre=None, phone=None, country_id=None, **post):
        """Buy votes: the number of a pack or another number, the WhatsApp (Mobile Money) number, then
        the page of the payment."""
        contest = contest_or_404(slug)
        candidate = self._candidate(contest, number)
        env = request.env
        values = {"votes": votes, "autre": autre, "phone": phone, "country_id": country_id}
        count = int(autre) if votes == "autre" and str(autre or "").isdigit() else (
            int(votes) if str(votes or "").isdigit() else 0)
        country = env["res.country"].sudo().browse(int(country_id or 0)).exists() or common.default_country()
        number_typed = common.normalize_phone(country, phone)
        if not number_typed:
            return self._render_candidate(contest, candidate, error=common.phone_error(country), values=values)
        partner = env["ocd.vendor.follower"].sudo()._ocd_contact(number_typed)
        if not partner.country_id:
            partner.country_id = country
        try:
            vote = env["ocd.vote"].sudo()._ocd_create(candidate, count, partner, "page")
        except UserError as exc:
            return self._render_candidate(contest, candidate, error=exc.args[0], values=values)
        return request.redirect(vote._ocd_page_path())

    # === THE PAYMENT, THE VOTES COUNTED === #

    def _vote(self, vote_id, token):
        vote = request.env["ocd.vote"].sudo().browse(vote_id).exists()
        if not vote or not vote._ocd_check_token(token):
            raise request.not_found()
        return vote

    @http.route("/vote/voix/<int:vote_id>", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def vote_page(self, vote_id, t=None, changer=None, **kwargs):
        vote = self._vote(vote_id, t)
        env = request.env
        contest, candidate, order = vote.contest_id, vote.candidate_id, vote.order_id
        state = vote._ocd_payment_state()
        last = order.transaction_ids.sorted("id")[-1:]
        if changer and state == "waiting" and last.state == "pending":
            state = "form"
        total = common.money(order.amount_total, order.currency_id)
        rows, hidden = ranking_rows(contest)
        row = next((row for row in rows if row["candidate"] == candidate), None)
        values = {
            "vote": vote,
            "contest": contest,
            "candidate": candidate,
            "order": order,
            "state": state,
            "tx": last,
            "token": t,
            "total": total,
            "what": env._("%(votes)s votes for %(candidate)s", votes=vote.votes, candidate=candidate._ocd_label()),
            "top": rows[:3],
            "hidden": hidden,
            "status_url": f"/vote/voix/{vote.id}/statut",
            "change_url": f"{vote._ocd_page_path()}&changer=1",
            "again_url": candidate._ocd_public_path(),
            "share_text": env._("I voted for %(name)s, N° %(number)s, in %(contest)s. Vote too:",
                                name=candidate.name, number=candidate.number, contest=contest.name),
            "share_url": request.httprequest.url_root.rstrip("/") + candidate._ocd_public_path(),
        }
        if state == "done":
            values["counted_title"] = env._("%(votes)s votes for %(name)s, it is counted", votes=vote.votes,
                                            name=candidate.name) if vote.votes > 1 else env._(
                "1 vote for %s, it is counted", candidate.name)
        if state == "done" and row:
            values["counted_line"] = env._(
                "%(name)s (N° %(number)s) now has %(votes)s votes: %(rank)s.", name=candidate.name,
                number=candidate.number, votes=contest._ocd_number(row["votes"]), rank=contest._ocd_rank_label(row["rank"]),
            ) if not hidden else env._("Your votes count for %s. The numbers are hidden until the results.", candidate.name)
            values["receipt"] = " · ".join(part for part in (
                env._("%s votes", vote.votes), total, vote.payment_method,
            ) if part)
            values["receipt_when"] = env._("Paid on %(day)s at %(hour)s · reference %(reference)s",
                                           day=tools.day_text(env, contest._ocd_local(vote.paid_at).date(), "d MMM"),
                                           hour=contest._ocd_hour(contest._ocd_local(vote.paid_at)),
                                           reference=vote.payment_reference or order.name)
        if state in ("form", "failed"):
            payment = OcdLivePayment()._payment_form_values(order, env._("Pay %s", total))
            payment["landing_route"] = vote._ocd_page_path()
            values.update(payment)
            values["no_method"] = not (values.get("payment_methods_sudo") or values.get("tokens_sudo"))
            values["help_whatsapp"] = tools.whatsapp_url(common.company().phone, env._(
                "Hello, I want to pay my votes %(order)s (%(total)s) from %(country)s.",
                order=order.name, total=total, country=order.partner_id.country_id.name or "",
            ))
        return request.render("ocd_vote.vote_page", common.page_values(
            False,
            nav="votes",
            back=candidate._ocd_public_path() if state in ("form", "failed") else False,
            header_title=env._("My votes"),
            **values,
        ))

    @http.route("/vote/voix/<int:vote_id>/statut", type="jsonrpc", auth="public", website=True)
    def vote_status(self, vote_id, access_token=None):
        """Polled by the page while the payment is in progress."""
        return {"state": self._vote(vote_id, access_token)._ocd_payment_state()}

    @http.route("/vote/voix/<int:vote_id>/envoye", type="http", auth="public", website=True, sitemap=False,
                methods=["POST"])
    def vote_announced(self, vote_id, t=None, reference=None, **post):
        """« I paid »: the Mobile Money checked by the team was sent."""
        vote = self._vote(vote_id, t)
        order = vote.order_id
        last = order.transaction_ids.sorted("id")[-1:]
        if vote._ocd_payment_state() == "waiting" and last.state == "pending" and last.provider_code == "custom":
            order._ocd_announce_payment(common.clean_text(reference, 60))
        return request.redirect(vote._ocd_page_path())

    # === THE RANKING, THE BAND, THE RESULTS === #

    def _ranking_values(self, contest):
        rows, hidden = ranking_rows(contest)
        return {
            "contest": contest,
            "rows": rows,
            "hidden": hidden,
            "open": contest._ocd_is_open(),
            "left": contest._ocd_left_text() if contest._ocd_is_open() else False,
        }

    @http.route("/vote/<string:slug>/classement", type="http", auth="public", website=True, sitemap=False, ocd_cache=10)
    def ranking(self, slug, **kwargs):
        contest = contest_or_404(slug)
        return request.render("ocd_vote.ranking", common.page_values(
            False, nav="votes", back=f"/vote/{contest.slug}", header_title=request.env._("Live ranking"),
            **self._ranking_values(contest),
        ))

    @http.route("/vote/<string:slug>/classement/liste", type="http", auth="public", website=True, sitemap=False,
                ocd_cache=5)
    def ranking_list(self, slug, **kwargs):
        """The rows of the ranking, read again by the page every 10 seconds (vote.js)."""
        contest = contest_or_404(slug)
        return request.render("ocd_vote.ranking_rows", {**self._ranking_values(contest), "request": request})

    def _band(self, slug, secret):
        contest = contest_or_404(slug)
        if not secret or not consteq(contest.sudo()._ocd_secret(), secret):
            raise request.not_found()
        return contest

    def _band_values(self, contest):
        values = self._ranking_values(contest)
        values["rows"] = values["rows"][:5]
        url = request.httprequest.url_root.rstrip("/") + f"/vote/{contest.slug}"
        env = request.env
        number = common.company().phone or ""
        label = url.split("://", 1)[-1]
        values.update({
            "qr": tools.qr_data_uri(url, box_size=6),
            "left_line": env._("Votes close in %s", values["left"]) if values["left"]
            else env._("Results") if contest.state == "done" else False,
            "foot_line": env._("Vote now: %(url)s or on WhatsApp VOTE + number to %(number)s", url=label, number=number)
            if number else env._("Vote now: %s", label),
        })
        return values

    @http.route("/vote/<string:slug>/bandeau/<string:secret>", type="http", auth="public", website=True,
                sitemap=False, ocd_cache=5)
    def band(self, slug, secret, **kwargs):
        """The band of the final, a page for the live software (OBS): the 5 first, how to vote."""
        contest = self._band(slug, secret)
        return request.render("ocd_vote.band", self._band_values(contest))

    @http.route("/vote/<string:slug>/resultats", type="http", auth="public", website=True, sitemap=False, ocd_cache=60)
    def results(self, slug, **kwargs):
        contest = contest_or_404(slug)
        if contest.state != "done":
            return request.redirect(f"/vote/{contest.slug}/classement")
        rows, _hidden = ranking_rows(contest)
        winner = rows[0]["candidate"] if rows and rows[0]["votes"] else False
        env = request.env
        return request.render("ocd_vote.results", common.page_values(
            False, nav="votes", back=f"/vote/{contest.slug}", header_title=env._("Results"),
            contest=contest, rows=rows, winner=winner,
            winner_title=env._("%(name)s wins %(contest)s", name=winner.name, contest=contest.name) if winner else False,
            winner_line=env._("With %(votes)s votes of %(total)s. Thank you to the %(voters)s people who voted.",
                              votes=contest._ocd_number(rows[0]["votes"]), total=contest._ocd_number(contest.vote_count),
                              voters=contest._ocd_number(contest.voter_count)) if winner else False,
            signature=contest._ocd_signature(),
        ))

    # === THE FINAL: TELL ME === #

    @http.route("/vote/<string:slug>/finale", type="http", auth="public", website=True, sitemap=False, methods=["POST"])
    def final_alert(self, slug, phone=None, country_id=None, **post):
        contest = contest_or_404(slug)
        partner = visitor_partner()
        if not partner:
            country = request.env["res.country"].sudo().browse(int(country_id or 0)).exists() or common.default_country()
            number = common.normalize_phone(country, phone)
            if not number:
                return request.redirect(f"/vote/{contest.slug}#finale")
            partner = request.env["ocd.vendor.follower"].sudo()._ocd_contact(number)
        Alert = request.env["ocd.vote.alert"].sudo()
        if contest.final_at and not Alert.search_count([("contest_id", "=", contest.id), ("partner_id", "=", partner.id)]):
            Alert.create({"contest_id": contest.id, "partner_id": partner.id})
            partner._ocd_agree_by_following()
        return request.redirect(f"/vote/{contest.slug}?prevenu=1#finale")

    # === THE PHOTOS === #

    @http.route("/vote/photo/<int:candidate_id>", type="http", auth="public", website=True, sitemap=False)
    def candidate_photo(self, candidate_id, v=None, **kwargs):
        candidate = request.env["ocd.vote.candidate"].sudo().browse(candidate_id).exists()
        if not candidate or not candidate.photo or not candidate._ocd_shown() or not candidate.contest_id._ocd_public():
            raise request.not_found()
        stream = request.env["ir.binary"]._get_image_stream_from(candidate, "photo", width=640, height=640)
        return common.media_response(stream, True, version=v)

    @http.route("/vote/image/<int:contest_id>", type="http", auth="public", website=True, sitemap=False)
    def contest_image(self, contest_id, v=None, **kwargs):
        contest = request.env["ocd.vote.contest"].sudo().browse(contest_id).exists()
        if not contest or not contest.image or not contest._ocd_public():
            raise request.not_found()
        stream = request.env["ir.binary"]._get_image_stream_from(contest, "image", width=1280, height=720)
        return common.media_response(stream, True, version=v)
