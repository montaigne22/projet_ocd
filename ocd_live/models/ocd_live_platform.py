import json
import re
from urllib.parse import urlsplit

from odoo import api, fields, models
from odoo.exceptions import ValidationError

DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")


class OcdLivePlatform(models.Model):
    """A platform where the lives take place (TikTok, Facebook, Instagram, YouTube...): it is
    recognised from the link of a live, and its name is said on the pages (« Watch on
    TikTok »). The team adds the others (OCD Live > Configuration > Live platforms)."""

    _name = "ocd.live.platform"
    _description = "Live Platform"
    _order = "sequence, id"
    _clear_cache_name = "default"  # _ocd_domains() follows the platforms

    name = fields.Char(required=True)
    code = fields.Char(required=True, help="Technical key of the platform, e.g. tiktok.")
    domains = fields.Char(
        string="Addresses Of Its Links",
        required=True,
        help="The addresses of the links of its lives, separated by commas, e.g. « tiktok.com, vm.tiktok.com ». "
        "The addresses below them are included (m.facebook.com for facebook.com).",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _unique_code = models.Constraint("UNIQUE (code)", "Another platform has this key.")

    @api.constrains("domains")
    def _check_domains(self):
        for platform in self:
            domains = platform._ocd_domain_list()
            if not domains or not all(DOMAIN_RE.match(domain) for domain in domains):
                raise ValidationError(self.env._(
                    "Write the addresses of the links of %s without https:// nor /, separated by commas, "
                    "e.g. tiktok.com, vm.tiktok.com.", platform.name,
                ))

    def _ocd_domain_list(self):
        self.ensure_one()
        return [
            domain.strip().lower().removeprefix("www.")
            for domain in (self.domains or "").split(",") if domain.strip()
        ]

    @api.model
    @api.ormcache()
    def _ocd_domains(self):
        """((domain, platform id), ...) of the active platforms, in their order."""
        return tuple(
            (domain, platform.id)
            for platform in self.sudo().search([])
            for domain in platform._ocd_domain_list()
        )

    @api.model
    def _ocd_for_url(self, url):
        """The active platform of a https link of a live, or an empty recordset."""
        try:
            parts = urlsplit((url or "").strip())
        except ValueError:
            return self.browse()
        if parts.scheme != "https" or not parts.hostname:
            return self.browse()
        host = parts.hostname.lower().removeprefix("www.")
        for domain, platform_id in self._ocd_domains():
            if host == domain or host.endswith("." + domain):
                return self.browse(platform_id)
        return self.browse()

    @api.model
    def _ocd_names_text(self):
        """« TikTok, Facebook, Instagram or YouTube »: the active platforms, for the messages."""
        names = self.sudo().search([]).mapped("name")
        if len(names) <= 1:
            return names[0] if names else ""
        return self.env._("%(first)s or %(last)s", first=", ".join(names[:-1]), last=names[-1])

    @api.model
    def _ocd_domains_json(self):
        """[[domain, name], ...] of the active platforms, for the forms that check a link on the
        phone of the vendor."""
        names = {platform.id: platform.name for platform in self.sudo().search([])}
        return json.dumps([[domain, names[platform_id]] for domain, platform_id in self._ocd_domains()])
