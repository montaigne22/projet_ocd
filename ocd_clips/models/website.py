from odoo import models

# The videos and the images of the clips, sent by the CDN with the other media of the site
CLIP_CDN_FILTER = "^/ocd/clips/[0-9]+/(video|image)"


class Website(models.Model):
    _inherit = "website"

    def _ocd_set_cdn(self, url):
        super()._ocd_set_cdn(url)
        if url:
            self._ocd_add_clip_cdn_filter()

    def _ocd_add_clip_cdn_filter(self):
        for website in self.filtered("cdn_activated"):
            filters = [line for line in (website.cdn_filters or "").splitlines() if line.strip()]
            if CLIP_CDN_FILTER not in filters:
                website.cdn_filters = "\n".join([*filters, CLIP_CDN_FILTER])
