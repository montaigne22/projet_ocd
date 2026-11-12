from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain

MODES = [("both", "At the studio and remote"), ("studio", "At the studio"), ("remote", "Remote")]


class OcdLiveAccount(models.Model):
    """An account of OCD Live on a platform of lives (TikTok first): the lives at the studio go
    on it, and the vendor of a remote live joins it as a guest, from their phone. The team sets
    several (one per country, one for the studio...): each live takes the first one that fits
    its mode and the country of its vendor, free at its hour; the team can change it."""

    _name = "ocd.live.account"
    _description = "Live Account Of OCD Live"
    _order = "sequence, id"
    _check_company_auto = True

    name = fields.Char(required=True, help="As the team calls it, e.g. « OCD Live Togo ».")
    platform_id = fields.Many2one(
        comodel_name="ocd.live.platform",
        string="Platform",
        required=True,
        ondelete="restrict",
        default=lambda self: self.env.ref("ocd_live.platform_tiktok", raise_if_not_found=False),
    )
    handle = fields.Char(
        string="Name On The Platform",
        required=True,
        help="As the vendors find it on the platform, e.g. @ocdlive.tg: the vendor of a remote live "
        "follows it and accepts its invitation.",
    )
    live_url = fields.Char(
        string="Link Of Its Lives",
        required=True,
        help="The https link where its lives are watched, e.g. https://www.tiktok.com/@ocdlive.tg/live",
    )
    mode = fields.Selection(selection=MODES, string="Lives", required=True, default="both")
    country_ids = fields.Many2many(
        comodel_name="res.country",
        string="Countries Of The Vendors",
        help="The lives of the vendors of these countries go on this account. Empty: all the countries.",
    )
    note = fields.Char(help="For the team, e.g. who holds the phone of the account.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    booking_count = fields.Integer(string="Next Lives", compute="_compute_booking_count")

    @api.constrains("live_url", "platform_id")
    def _check_live_url(self):
        Platform = self.env["ocd.live.platform"].sudo()
        for account in self:
            if Platform._ocd_for_url(account.live_url) != account.platform_id:
                raise ValidationError(self.env._(
                    "The link of the lives of %(account)s must be a https link on %(platform)s.",
                    account=account.name, platform=account.platform_id.name,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        accounts = super().create(vals_list)
        self.env["ocd.live.booking"]._ocd_assign_accounts()
        return accounts

    def write(self, vals):
        result = super().write(vals)
        if any(key in vals for key in ("mode", "country_ids", "active", "company_id", "sequence")):
            self.env["ocd.live.booking"]._ocd_assign_accounts()
        return result

    def unlink(self):
        result = super().unlink()
        self.env["ocd.live.booking"]._ocd_assign_accounts()
        return result

    def _compute_booking_count(self):
        counts = dict(self.env["ocd.live.booking"]._read_group(
            [("account_id", "in", self.ids), ("state", "in", ("draft", "confirmed")),
             ("end_datetime", ">", fields.Datetime.now())],
            ["account_id"], ["__count"],
        ))
        for account in self:
            account.booking_count = counts.get(account, 0)

    def action_ocd_view_bookings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": "ocd.live.booking",
            "view_mode": "list,calendar,form",
            "domain": [("account_id", "=", self.id)],
            "context": {"search_default_coming": 1},
        }

    def _ocd_fits(self, mode, country):
        """Whether the account takes the lives of `mode` of a vendor of `country`."""
        self.ensure_one()
        return self.mode in (mode, "both") and (not self.country_ids or country in self.country_ids)

    @api.model
    def _ocd_pick(self, booking):
        """The account of `booking`: the accounts of its country first, then the others, in
        their order; among them the first one without another live at its hour."""
        if not booking.mode or not booking.company_id:
            return self.browse()
        country = booking.partner_id.country_id
        accounts = self.sudo().search([("company_id", "=", booking.company_id.id), ("mode", "in", (booking.mode, "both"))])
        accounts = accounts.filtered(lambda account: account._ocd_fits(booking.mode, country))
        accounts = accounts.sorted(lambda account: (not account.country_ids, account.sequence, account.id))
        if len(accounts) > 1 and booking.start_datetime and booking.end_datetime:
            domain = Domain([
                ("account_id", "in", accounts.ids),
                ("state", "in", ("draft", "confirmed")),
                ("start_datetime", "<", booking.end_datetime),
                ("end_datetime", ">", booking.start_datetime),
            ])
            if booking.id:
                domain &= Domain("id", "!=", booking.id)
            busy = self.env["ocd.live.booking"].sudo().search(domain).account_id
            return (accounts - busy)[:1] or accounts[:1]
        return accounts[:1]
