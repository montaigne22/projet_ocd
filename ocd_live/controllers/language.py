from odoo import http
from odoo.http import request

from . import common


class OcdLanguage(http.Controller):

    @http.route("/ocd/langue/<string:code>", type="http", auth="public", website=True, multilang=False, sitemap=False)
    def language(self, code, r="/", **kwargs):
        """The language button of the pages (page_languages): keep the choice, then show the page
        `r` in that language. Like /website/lang of Odoo, but the choice is the last cookie of the
        answer: for a browser that never chose, Odoo writes the language it guessed after the one
        of /website/lang, and the browser kept the guessed one."""
        lang = request.env["res.lang"]._get_data(url_code=code)
        website = request.env.website
        if not lang or lang.code not in website.language_ids.mapped("code"):
            raise request.not_found()
        # The address in the language chosen: Odoo adds or removes its code (/fr/…)
        request.update_context(lang=lang.code)
        response = request.redirect(common.local_path(r, "/"))
        request.future_response.set_cookie("frontend_lang", lang.code, max_age=365 * 24 * 60 * 60)
        return response
