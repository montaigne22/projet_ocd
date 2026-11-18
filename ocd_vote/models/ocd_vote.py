import secrets
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import consteq

# Votes bought at once, at most (another number than the packs)
MAX_VOTES = 10000


class OcdVote(models.Model):
    """The votes bought with one payment: they count once the payment is confirmed, never before,
    and stop counting if it is refunded. A payment started after the end of the votes does not
    count (it is refunded by the team)."""

    _name = "ocd.vote"
    _description = "Votes Of One Payment"
    _inherit = ["mail.thread"]
    _order = "id desc"

    contest_id = fields.Many2one(comodel_name="ocd.vote.contest", required=True, index=True, ondelete="restrict")
    candidate_id = fields.Many2one(comodel_name="ocd.vote.candidate", required=True, index=True, ondelete="restrict")
    company_id = fields.Many2one(related="contest_id.company_id", store=True)
    currency_id = fields.Many2one(related="contest_id.currency_id")
    votes = fields.Integer(required=True)
    amount_company = fields.Monetary(string="Amount", required=True, help="In the currency of the company.")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Voter", required=True, index=True)
    phone = fields.Char(related="partner_id.phone", string="Phone Of The Voter")
    source = fields.Selection(selection=[("page", "Page"), ("whatsapp", "WhatsApp")], required=True, default="page")
    order_id = fields.Many2one(comodel_name="sale.order", string="Order", index=True, readonly=True, copy=False)
    state = fields.Selection(
        selection=[
            ("pending", "Waiting for the payment"),
            ("paid", "Counted"),
            ("late", "Paid after the end: to refund"),
            ("refunded", "Refunded"),
            ("cancelled", "Not paid"),
        ],
        required=True, default="pending", index=True, tracking=True,
    )
    paid_at = fields.Datetime(readonly=True, copy=False)
    payment_reference = fields.Char(compute="_compute_payment", string="Payment Reference")
    payment_method = fields.Char(compute="_compute_payment", string="Paid With")
    access_token = fields.Char(copy=False, groups="base.group_system")

    @api.depends("order_id.transaction_ids.state")
    def _compute_payment(self):
        for vote in self:
            tx = vote.order_id.transaction_ids.filtered(lambda tx: tx.state == "done")[:1]
            vote.payment_reference = tx.provider_reference or tx.reference or False
            vote.payment_method = tx.payment_method_id.name or tx.provider_id.name or False

    @api.depends("votes", "candidate_id")
    def _compute_display_name(self):
        for vote in self:
            vote.display_name = self.env._("%(votes)s votes for %(candidate)s",
                                           votes=vote.votes, candidate=vote.candidate_id._ocd_label())

    # === BUY === #

    @api.model
    def _ocd_create(self, candidate, votes, partner, source="page"):
        """`partner` buys `votes` votes for `candidate`: the order to pay (the price of a pack when
        the number is the one of a pack) and its votes, waiting for the payment."""
        candidate = candidate.sudo()
        contest = candidate.contest_id
        if not contest._ocd_is_open():
            raise UserError(self.env._("The votes of %s are not open.", contest.name))
        if not candidate._ocd_shown():
            raise UserError(self.env._("This candidate cannot get votes."))
        votes = int(votes or 0)
        if not 1 <= votes <= MAX_VOTES:
            raise UserError(self.env._("Choose between 1 and %s votes.", MAX_VOTES))
        price = contest._ocd_price(votes)
        company = contest.company_id
        product = self.env.ref("ocd_vote.product_vote").sudo().product_variant_id
        order = self.env["sale.order"].sudo().with_company(company).create({
            "partner_id": partner.id,
            "company_id": company.id,
            "require_signature": False,
            # A positive prepayment makes the payment form ask for the payment of the order
            "prepayment_percent": 1.0,
            "order_line": [fields.Command.create({
                "product_id": product.id,
                "product_uom_qty": 1,
                "name": self.env._("%(votes)s votes for %(candidate)s · %(contest)s", votes=votes,
                                   candidate=candidate._ocd_label(), contest=contest.name),
                "tax_ids": [fields.Command.clear()],
            })],
        })
        line = order.order_line[:1]
        line.price_unit = company.currency_id._convert(price, order.currency_id, company, fields.Date.today())
        return self.sudo().create({
            "contest_id": contest.id,
            "candidate_id": candidate.id,
            "votes": votes,
            "amount_company": price,
            "partner_id": partner.id,
            "source": source,
            "order_id": order.id,
            "access_token": secrets.token_urlsafe(18),
        })

    def _ocd_check_token(self, token):
        self.ensure_one()
        stored = self.sudo().access_token or ""
        return bool(stored and token and consteq(stored, str(token)))

    def _ocd_page_path(self):
        self.ensure_one()
        return f"/vote/voix/{self.id}?t={self.sudo().access_token}"

    # === PAID === #

    def _ocd_on_paid(self):
        """The payment of the order is confirmed: the votes count, unless the payment started
        after the end of the votes (then the team refunds it)."""
        now = fields.Datetime.now()
        counted = self.browse()
        for vote in self.sudo().filtered(lambda vote: vote.state in ("pending", "cancelled")):
            transactions = vote.order_id.transaction_ids.sorted("id")
            started = transactions[:1].create_date or now
            if started > vote.contest_id.date_close or vote.contest_id.state in ("done", "cancelled"):
                vote.write({"state": "late", "paid_at": now})
                vote.message_post(body=self.env._("Paid after the end of the votes: to refund."))
                continue
            vote.write({"state": "paid", "paid_at": now})
            counted |= vote
        if counted and self.env["ocd.automation"]._ocd_enabled("vote_paid"):
            counted._ocd_tell_paid()
        return counted

    def _ocd_tell_paid(self):
        """Tell the voter their votes are counted (ocd_vote_whatsapp)."""

    def action_ocd_refund(self):
        """The team refunded the payment: its votes no longer count."""
        for vote in self:
            if vote.state not in ("paid", "late"):
                continue
            vote.state = "refunded"
            vote.message_post(body=self.env._("Refunded by %s: the votes no longer count.", self.env.user.name))
        return True

    @api.model
    def _ocd_cancel_unpaid(self, now=None):
        """The votes not paid in time (setting) are cancelled with their order; a payment checked by
        the team (Mobile Money sent) keeps waiting."""
        now = now or fields.Datetime.now()
        minutes = self.env.company.ocd_vote_pay_minutes
        votes = self.sudo().search([("state", "=", "pending"), ("create_date", "<", now - timedelta(minutes=minutes))])
        for vote in votes:
            if vote.order_id.transaction_ids.filtered(lambda tx: tx.state in ("pending", "authorized", "done")):
                continue
            vote.state = "cancelled"
            if vote.order_id.state in ("draft", "sent"):
                vote.order_id._action_cancel()

    # === THE PAGE OF THE VOTER === #

    def _ocd_payment_state(self):
        """form, waiting, failed, done (counted), late, refunded or cancelled."""
        self.ensure_one()
        if self.state == "paid":
            return "done"
        if self.state in ("late", "refunded", "cancelled"):
            return self.state
        return self.order_id._ocd_payment_state()


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ocd_vote_ids = fields.One2many(comodel_name="ocd.vote", inverse_name="order_id", string="Votes")

    def _action_confirm(self):
        """Override of `sale`: the payment confirms the order, the votes count (never the
        browser)."""
        result = super()._action_confirm()
        self.ocd_vote_ids._ocd_on_paid()
        return result

    def _action_cancel(self):
        result = super()._action_cancel()
        self.ocd_vote_ids.filtered(lambda vote: vote.state == "pending").sudo().write({"state": "cancelled"})
        return result
