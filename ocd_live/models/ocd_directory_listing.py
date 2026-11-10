from urllib.parse import urlsplit

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

ALLOWED_HOSTS = {
    "tiktok.com": "tiktok",
    "vm.tiktok.com": "tiktok",
    "facebook.com": "facebook",
    "fb.watch": "facebook",
    "m.facebook.com": "facebook",
    "instagram.com": "instagram",
    "youtube.com": "youtube",
    "m.youtube.com": "youtube",
    "youtu.be": "youtube",
}


def _platform_of(url):
    """Return the platform of a live link, or False if it is not a supported https link."""
    try:
        parts = urlsplit((url or "").strip())
    except ValueError:
        return False
    if parts.scheme != "https" or not parts.hostname:
        return False
    host = parts.hostname.lower()
    if host.startswith("www."):
        host = host[4:]
    if host in ALLOWED_HOSTS:
        return ALLOWED_HOSTS[host]
    for domain, platform in ALLOWED_HOSTS.items():
        if host.endswith("." + domain):
            return platform
    return False


class OcdDirectoryListing(models.Model):
    """Live link sent by a vendor to appear in the directory during a checking window."""

    _name = "ocd.directory.listing"
    _description = "Directory Live Link"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "window_start desc, id desc"
    _check_company_auto = True

    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Vendor", required=True, index=True, tracking=True
    )
    business = fields.Char(related="partner_id.ocd_business")
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    url = fields.Char(string="Live Link", required=True, tracking=True)
    platform = fields.Selection(
        selection=[
            ("tiktok", "TikTok"),
            ("facebook", "Facebook"),
            ("instagram", "Instagram"),
            ("youtube", "YouTube"),
        ],
        compute="_compute_platform",
        store=True,
    )
    country_id = fields.Many2one(comodel_name="res.country", string="Country", index=True)
    category_id = fields.Many2one(comodel_name="ocd.live.category", string="Category", index=True)
    window_id = fields.Many2one(comodel_name="ocd.directory.window", string="Window")
    window_start = fields.Datetime(string="Window Start", index=True)
    window_end = fields.Datetime(string="Window End", index=True)
    state = fields.Selection(
        selection=[
            ("queued", "Waiting for the window"),
            ("to_check", "To check"),
            ("published", "Online"),
            ("refused", "Refused"),
            ("ended", "Ended"),
        ],
        required=True,
        default="queued",
        tracking=True,
        index=True,
    )
    refuse_reason_id = fields.Many2one(comodel_name="ocd.listing.refuse.reason", string="Refusal Reason")
    refuse_note = fields.Text(string="Note To The Vendor")
    checked_by_id = fields.Many2one(comodel_name="res.users", string="Checked By", readonly=True)
    checked_at = fields.Datetime(string="Checked At", readonly=True)

    _unique_open_link_per_vendor = models.UniqueIndex(
        "(partner_id) WHERE state IN ('queued', 'to_check', 'published')",
        "This vendor already has a link waiting or online.",
    )

    @api.depends("url")
    def _compute_platform(self):
        for listing in self:
            listing.platform = _platform_of(listing.url) or False

    @api.depends("partner_id", "platform")
    def _compute_display_name(self):
        for listing in self:
            listing.display_name = listing.partner_id.ocd_business or listing.partner_id.name or ""

    @api.constrains("url")
    def _check_url(self):
        for listing in self:
            if len(listing.url or "") > 500 or not _platform_of(listing.url):
                raise ValidationError(
                    self.env._("Send the https link of a live on TikTok, Facebook, Instagram or YouTube.")
                )

    # === SUBMISSION === #

    @api.model
    def _ocd_submit(self, partner, url, category=None):
        """Register the link sent by `partner` for the current or next checking window."""
        partner.ensure_one()
        if not partner.ocd_pass_active:
            raise UserError(self.env._("A directory pass is needed to send a live link."))
        if partner.ocd_vendor_state == "refused":
            raise UserError(self.env._("This vendor cannot send links to the directory."))
        url = (url or "").strip()
        if not _platform_of(url):
            raise UserError(
                self.env._("Send the https link of a live on TikTok, Facebook, Instagram or YouTube.")
            )
        found = self.env["ocd.directory.window"]._ocd_find()
        if not found:
            raise UserError(self.env._("The directory is closed for now."))
        window, start, end = found
        now = fields.Datetime.now()
        # Write the pending state changes (e.g. a refusal) before the unique index checks them
        self.flush_model(["state", "partner_id"])
        # sudo: called from the vendor space, the vendor was identified by the personal link
        return self.sudo().create({
            "partner_id": partner.id,
            "url": url,
            "country_id": partner.country_id.id,
            "category_id": (category or partner.ocd_category_id).id,
            "window_id": window.id,
            "window_start": start,
            "window_end": end,
            "state": "to_check" if start <= now else "queued",
        })

    # === ACTIONS === #

    def action_publish(self):
        now = fields.Datetime.now()
        for listing in self:
            if listing.state not in ("to_check", "refused"):
                raise UserError(self.env._("Only a link to check can be published."))
            if listing.window_end and listing.window_end <= now:
                raise UserError(self.env._("The window of this link is over."))
        self.write({
            "state": "published",
            "checked_by_id": self.env.uid,
            "checked_at": now,
            "refuse_reason_id": False,
        })
        for listing in self:
            listing._ocd_notify_vendor("published")
        return True

    def action_open_refuse_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Refuse the link"),
            "res_model": "ocd.directory.listing.refuse",
            "view_mode": "form",
            "target": "new",
            "context": {"default_listing_ids": self.ids},
        }

    def _ocd_refuse(self, reason, note=False):
        self.write({
            "state": "refused",
            "refuse_reason_id": reason.id,
            "refuse_note": note,
            "checked_by_id": self.env.uid,
            "checked_at": fields.Datetime.now(),
        })
        for listing in self:
            listing._ocd_notify_vendor("refused")

    def action_end(self):
        self.filtered(lambda l: l.state in ("queued", "to_check", "published")).write({"state": "ended"})
        return True

    def _ocd_notify_vendor(self, event):
        """Tell the vendor that the link is online or refused. Extended by ocd_live_whatsapp."""
        self.ensure_one()
        if event == "published":
            body = self.env._("The live link is online in the directory.")
        else:
            body = self.env._(
                "The live link was refused: %s",
                self.refuse_note or self.refuse_reason_id.message or self.refuse_reason_id.name or "",
            )
        self.message_post(body=body)

    @api.model
    def _cron_update_windows(self):
        """Open the queued links at the start of their window, end them at its end."""
        now = fields.Datetime.now()
        self.search([("state", "=", "queued"), ("window_start", "<=", now)]).write({"state": "to_check"})
        self.search([("state", "in", ("queued", "to_check", "published")), ("window_end", "<=", now)]).write(
            {"state": "ended"}
        )
