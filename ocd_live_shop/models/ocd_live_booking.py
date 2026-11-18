import logging
import re
import threading
import time
from collections import Counter
from urllib.parse import parse_qs, urlparse

import psycopg2

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.modules import module as odoo_module

_logger = logging.getLogger(__name__)

# The visits of the boutiques during the lives, counted by each worker and written together every
# few seconds: thousands of visitors at once would otherwise all wait on the row of the live, and
# the control room with them when it changes the product on screen
VISITS_SECONDS = 5
_visits = Counter()  # (database, live) -> visits not written yet
_visits_lock = threading.Lock()
_visits_written = [0.0]


def _add_visits(cr, counts):
    for live, count in counts.items():
        cr.execute(
            "UPDATE ocd_live_booking SET ocd_visit_count = COALESCE(ocd_visit_count, 0) + %s WHERE id = %s",
            [count, live],
        )


class OcdLiveBooking(models.Model):
    _inherit = "ocd.live.booking"

    current_product_tmpl_id = fields.Many2one(
        comodel_name="product.template", string="Shown Now", copy=False
    )
    moment_ids = fields.One2many(
        comodel_name="ocd.live.moment", inverse_name="booking_id", string="Moments Of The Replay"
    )
    ocd_started_at = fields.Datetime(
        string="Started At", copy=False, readonly=True,
        help="« The live starts » touched in the control room: the moments of the replay (and their clips) "
        "count from it. Empty: from the hour booked.",
    )
    ocd_visit_count = fields.Integer(
        string="Boutique Visits",
        copy=False,
        readonly=True,
        help="Visits of the boutique of the vendor during the live, one per browser.",
    )
    vendor_product_ids = fields.Many2many(
        comodel_name="product.template",
        string="Products Of The Vendor",
        compute="_compute_vendor_product_ids",
    )

    @api.depends("partner_id")
    def _compute_vendor_product_ids(self):
        products = self.env["product.template"].search([
            ("ocd_vendor_id", "in", self.partner_id.ids),
            ("sale_ok", "=", True),
            ("ocd_review_state", "=", "approved"),
        ])
        by_vendor = products.grouped("ocd_vendor_id")
        for booking in self:
            booking.vendor_product_ids = by_vendor.get(booking.partner_id, self.env["product.template"])

    def _ocd_show_product(self, product):
        """Show `product` on the boutique of the vendor and note the moment for the replay."""
        self.ensure_one()
        if self.state not in ("confirmed", "done"):
            raise UserError(self.env._("The live is not confirmed."))
        if product.ocd_vendor_id != self.partner_id:
            raise UserError(self.env._("This product does not belong to the vendor of the live."))
        now = fields.Datetime.now()
        self.current_product_tmpl_id = product
        self.env["ocd.live.moment"].create({
            "booking_id": self.id,
            "product_tmpl_id": product.id,
            "shown_at": now,
            "offset_seconds": self._ocd_offset_of(now),
        })

    def _ocd_live_start(self):
        """The real start of the live: « The live starts » in the control room, else the hour booked."""
        self.ensure_one()
        return self.ocd_started_at or self.start_datetime

    def _ocd_offset_of(self, moment):
        """The second of the live (from its real start) of the datetime `moment`."""
        self.ensure_one()
        return max(int((moment - self._ocd_live_start()).total_seconds()), 0)

    def _ocd_mark_started(self, when=None):
        """« The live starts » (once): the moments already noted count again from it, so that a live
        that starts late does not shift its replay and its clips."""
        self.ensure_one()
        if self.state not in ("confirmed", "done"):
            raise UserError(self.env._("The live is not confirmed."))
        if self.ocd_started_at:
            return False
        self.ocd_started_at = when or fields.Datetime.now()
        for moment in self.moment_ids.filtered("shown_at"):
            moment.offset_seconds = self._ocd_offset_of(moment.shown_at)
        return True

    def _ocd_count_visit(self):
        """Count a visit of the boutique during the live (one per browser)."""
        self.ensure_one()
        with _visits_lock:
            _visits[self.env.cr.dbname, self.id] += 1
            due = time.monotonic() - _visits_written[0] >= VISITS_SECONDS
        if due or odoo_module.current_test:
            self._ocd_write_visits()

    @api.model
    def _ocd_write_visits(self):
        """Write the visits counted by this worker, in a transaction of their own that waits for
        the other workers a moment instead of failing (READ COMMITTED), never with the page."""
        dbname = self.env.cr.dbname
        with _visits_lock:
            counts = {live: count for (db, live), count in _visits.items() if db == dbname}
            for live in counts:
                del _visits[dbname, live]
            _visits_written[0] = time.monotonic()
        if not counts:
            return
        try:
            if odoo_module.current_test:
                _add_visits(self.env.cr, counts)  # the tests run in one transaction
            else:
                with self.env.registry.cursor() as cr:
                    cr.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                    _add_visits(cr, counts)
        except psycopg2.Error:
            # An indication for the control room: it never breaks the boutique
            _logger.warning("OCD Live: visits of the lives %s not written", counts, exc_info=True)
            return
        self.browse(list(counts)).invalidate_recordset(["ocd_visit_count"])

    def _ocd_replay_embed(self):
        """How the page plays the replay: {platform, id, seek}. YouTube and TikTok (a published
        video) play in the page and go to a moment; Facebook plays in the page from a moment;
        Instagram and the other links open on their site (no moment)."""
        self.ensure_one()
        url = (self.replay_url or "").strip()
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        for prefix in ("www.", "m.", "mobile.", "music."):
            host = host.removeprefix(prefix)
        if host in ("youtube.com", "youtube-nocookie.com", "youtu.be"):
            video = ""
            if host == "youtu.be":
                video = parsed.path.strip("/").split("/")[0]
            elif parsed.path == "/watch":
                video = (parse_qs(parsed.query).get("v") or [""])[0]
            else:
                match = re.match(r"^/(?:live|shorts|embed|v)/([^/?#]+)", parsed.path)
                video = match.group(1) if match else ""
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", video or ""):
                return {"platform": "youtube", "id": video, "seek": True}
        elif host.endswith("tiktok.com"):
            match = re.search(r"/video/(\d{8,25})", parsed.path)
            if match:
                return {"platform": "tiktok", "id": match.group(1), "seek": True}
        elif host == "fb.watch" or host.endswith("facebook.com"):
            if parsed.scheme == "https":
                return {"platform": "facebook", "id": url, "seek": True}
        elif host.endswith("instagram.com"):
            return {"platform": "instagram", "id": "", "seek": False}
        return {"platform": "", "id": "", "seek": False}

    def _ocd_replay_url_at(self, seconds):
        """Return the link of the replay at the second `seconds`, when the platform allows it
        (YouTube); the link of the replay otherwise."""
        self.ensure_one()
        url = self.replay_url or ""
        host = (urlparse(url).hostname or "").lower()
        if seconds and (host.endswith("youtube.com") or host == "youtu.be"):
            return f"{url}{'&' if '?' in url else '?'}t={int(seconds)}s"
        return url
