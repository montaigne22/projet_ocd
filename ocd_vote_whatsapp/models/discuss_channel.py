"""Vote on WhatsApp (chantier 4, design OcdVote): « VOTE 12 » to the WhatsApp of OCD Live. The
bot finds the candidate N° 12 of the contest open (asks which when several contests have this
number), asks how many votes (1, or the packs), then asks the payment on the phone: Mobile Money
by CamPay when it takes this number, otherwise the link of the page of the payment. The votes
count once paid, and the voter is told (ocd_vote_comptee)."""
import logging
import re

from odoo import fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.whatsapp_cloud.tools import simplify

_logger = logging.getLogger(__name__)

VOTE_RE = re.compile(r"^vote[rz]?\s*(?:n|no|numero)?\s*(\d{1,4})$")
PACK_PREFIX = "ocd_vote_pack_"
CONTEST_PREFIX = "ocd_vote_contest_"


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _whatsapp_get_step_handlers(self):
        return {**super()._whatsapp_get_step_handlers(), "ocd_vote_pack": self._ocd_step_vote_pack,
                "ocd_vote_contest": self._ocd_step_vote_contest}

    def _whatsapp_bot_answer(self, wa_message, content):
        """Override of `whatsapp_cloud_sale`: « VOTE 12 »."""
        match = VOTE_RE.match(simplify(wa_message.body or ""))
        if match:
            self._ocd_vote_number(int(match.group(1)))
            return True
        return super()._whatsapp_bot_answer(wa_message, content)

    def _ocd_vote_open_candidates(self, number):
        contests = self.env["ocd.vote.contest"].sudo().search([("state", "=", "approved")]).filtered(
            lambda contest: contest._ocd_is_open()
        )
        return contests.candidate_ids.filtered(lambda candidate: candidate.number == number and candidate._ocd_shown())

    def _ocd_vote_number(self, number):
        """The candidate N° `number`: her contest, then how many votes."""
        self.ensure_one()
        channel = self._whatsapp_customer_env()
        env = channel.env
        candidates = self._ocd_vote_open_candidates(number)
        if not candidates:
            open_contests = env["ocd.vote.contest"].sudo().search([("state", "=", "approved")]).filtered(
                lambda contest: contest._ocd_is_open())
            base = self.get_base_url()
            if open_contests:
                lines = [env._("No open contest has the number %s. The contests open:", number)]
                lines += [f"• {contest.name}: {base}/vote/{contest.slug}" for contest in open_contests[:5]]
                channel._whatsapp_send_answer("\n".join(lines))
            else:
                channel._whatsapp_send_answer(env._("No contest is open for votes now."))
            return
        if len(candidates) > 1:
            channel._whatsapp_ask(
                "ocd_vote_contest", env._("Several contests have the number %s: which one?", number),
                choices=[(f"{CONTEST_PREFIX}{candidate.id}", candidate.contest_id.name[:24], None)
                         for candidate in candidates[:10]],
                list_button=env._("Choose the contest"),
            )
            return
        self._ocd_vote_ask_pack(candidates)

    def _ocd_step_vote_contest(self, wa_message, content, data):
        reply_id = content.get("reply_id") or ""
        if not reply_id.startswith(CONTEST_PREFIX):
            return False
        candidate = self.env["ocd.vote.candidate"].sudo().browse(int(reply_id.removeprefix(CONTEST_PREFIX) or 0)).exists()
        if not candidate:
            return False
        self._ocd_vote_ask_pack(candidate)
        return True

    def _ocd_vote_ask_pack(self, candidate):
        self.ensure_one()
        channel = self._whatsapp_customer_env()
        env = channel.env
        contest = candidate.contest_id.with_context(env.context)
        ranking = {row["candidate"].id: row for row in contest._ocd_ranking()}
        row = ranking.get(candidate.id)
        if row and not contest._ocd_hidden():
            text = env._("%(contest)s · %(candidate)s (%(rank)s, %(votes)s votes). How many votes?",
                         contest=contest.name, candidate=candidate._ocd_label(), rank=contest._ocd_rank_label(row["rank"]),
                         votes=contest._ocd_number(row["votes"]))
        else:
            text = env._("%(contest)s · %(candidate)s. How many votes?", contest=contest.name,
                         candidate=candidate._ocd_label())
        choices = [(f"{PACK_PREFIX}{choice['votes']}", f"{choice['label']} · {choice['price_text']}", None)
                   for choice in contest._ocd_choices()[:3]]
        channel._whatsapp_ask("ocd_vote_pack", text, data={"candidate_id": candidate.id}, choices=choices)

    def _ocd_step_vote_pack(self, wa_message, content, data):
        """The number of votes chosen (a button, or a number written): the votes, then the payment."""
        reply_id = content.get("reply_id") or ""
        if reply_id.startswith(PACK_PREFIX):
            votes = int(reply_id.removeprefix(PACK_PREFIX) or 0)
        else:
            typed = re.sub(r"\D", "", wa_message.body or "")
            votes = int(typed) if typed and len(typed) <= 5 else 0
        candidate = self.env["ocd.vote.candidate"].sudo().browse(data.get("candidate_id")).exists()
        if not candidate or not votes:
            return False
        channel = self._whatsapp_customer_env()
        env = channel.env
        partner = self.whatsapp_partner_id
        try:
            vote = env["ocd.vote"].sudo()._ocd_create(candidate, votes, partner, "whatsapp")
        except UserError as exc:
            channel._whatsapp_send_answer(exc.args[0])
            return True
        if self._ocd_vote_request_on_phone(vote):
            channel._whatsapp_send_bot_text(env._(
                "A request of %s arrives on this number: type your Mobile Money code to pay. You are told once "
                "your votes are counted.", vote.contest_id._ocd_money(vote.amount_company),
            ))
        else:
            channel._whatsapp_send_answer(env._(
                "Pay your %(votes)s votes for %(candidate)s here: %(url)s", votes=vote.votes,
                candidate=candidate.name, url=f"{self.get_base_url()}{vote._ocd_page_path()}",
            ))
        return True

    def _ocd_vote_request_on_phone(self, vote):
        """Ask the payment on the phone of the voter when a Mobile Money provider takes it (CamPay);
        False otherwise (the link of the page of the payment is sent)."""
        order = vote.order_id
        provider = self.env["payment.provider"].sudo().search([
            ("code", "=", "campay"), ("company_id", "=", order.company_id.id),
        ], limit=1)
        phone = vote.partner_id.phone
        if not provider or not phone or not hasattr(provider, "_campay_normalize_phone") \
                or not provider._campay_normalize_phone(phone):
            return False
        method = provider.payment_method_ids[:1]
        if not method:
            return False
        Transaction = self.env["payment.transaction"].sudo()
        try:
            transaction = Transaction.create({
                "provider_id": provider.id,
                "payment_method_id": method.id,
                "amount": order.amount_total,
                "currency_id": order.currency_id.id,
                "partner_id": vote.partner_id.id,
                "reference": Transaction._compute_reference(provider.code, prefix=order.name),
                "operation": "online_direct",
                "sale_order_ids": [fields.Command.set(order.ids)],
            })
            transaction._campay_request_collect(phone)
        except (UserError, ValidationError):
            _logger.info("OCD Vote: Mobile Money request refused for %s, the link is sent", vote.id, exc_info=True)
            return False
        return True
