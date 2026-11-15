import functools
import re

from odoo import models
from odoo.http import request

from .. import page_cache

# Files of the site, photos and videos: the same for everyone, kept by the browsers and by the
# CDN in front of the site
MEDIA_PATH = re.compile(r"/(web/(assets|image)|[^/]+/static|lives/(image|carte|video))/")


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _dispatch(cls, endpoint):
        """The public pages whose route asks for it are kept in memory a few seconds (see
        ocd_live.page_cache)."""
        return page_cache.dispatch(endpoint, functools.partial(super()._dispatch, endpoint))

    @classmethod
    def _post_dispatch(cls, response):
        """A file, a photo or a video goes without cookies: a CDN keeps only the answers without
        cookies, and a visitor who opens one first needs no session for it. Asked without a
        session (by the CDN, or a first visit), it is what every visitor gets: the CDN may keep
        it too (Odoo lets only the browser keep the photos), and the pages of the site may use
        it from the address of the CDN (the browsers take the fonts of the icons from another
        address only with Access-Control-Allow-Origin)."""
        if MEDIA_PATH.match(request.httprequest.path):
            if not request.session.is_dirty:
                request.session.can_save = False
            headers = request.future_response.headers
            kept = [cookie for cookie in headers.getlist("Set-Cookie") if not cookie.startswith("frontend_lang=")]
            headers.remove("Set-Cookie")
            for cookie in kept:
                headers.add("Set-Cookie", cookie)
            if not request.httprequest.cookies.get("session_id") and hasattr(response, "cache_control"):
                response.headers["Access-Control-Allow-Origin"] = "*"
                cache_control = response.cache_control
                if response.status_code == 200 and cache_control.private and (cache_control.max_age or 0) > 0:
                    cache_control.pop("private", None)
                    cache_control.public = True
        super()._post_dispatch(response)
