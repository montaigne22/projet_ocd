"""What OCD Live brought a vendor, counted day by day (chantier 3 of the roadmap, design
MesChiffres): the taps on « Watch » of their lives (cards of the feed, boutique, messages to the
followers), the visits of their boutique (one per phone and per day), the customers who wrote
to them on WhatsApp from a product. The figures of the vendor read these counts: one row per
vendor, day (at the hour of the vendor), kind and record (the live, the product), never one row
per tap.

Counted like the visits of the boutiques during the lives (ocd_live_shop,
ocd_live_booking._ocd_count_visit): each worker keeps the taps in memory and writes them together
every few seconds, in a transaction of their own, so that a crowd never waits on the same row."""
import logging
import threading
import time
from collections import Counter
from datetime import date, timedelta

import psycopg2

from odoo import api, fields, models
from odoo.modules import module as odoo_module

from odoo.addons.ocd_live import tools

_logger = logging.getLogger(__name__)

COUNT_SECONDS = 5
# The counts are kept this long, then removed by the autovacuum (the figures go back 12 months)
KEPT_DAYS = 400
KINDS = [
    ("watch", "Opened From OCD"),
    ("visit", "Boutique Visit"),
    ("contact", "WhatsApp Contact"),
]

_counts = Counter()  # (database, vendor, day, kind, record) -> taps not written yet
_counts_lock = threading.Lock()
_counts_written = [0.0]


def _add_counts(cr, counts):
    for (vendor, day, kind, res_id), count in counts.items():
        cr.execute(
            """
            INSERT INTO ocd_vendor_count (vendor_id, day, kind, res_id, count) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (vendor_id, day, kind, res_id) DO UPDATE SET count = ocd_vendor_count.count + EXCLUDED.count
            """,
            [vendor, day, kind, res_id, count],
        )


class OcdVendorCount(models.Model):
    _name = "ocd.vendor.count"
    _description = "Figures Of A Vendor, Day By Day"
    _order = "day desc, id desc"
    _log_access = False

    vendor_id = fields.Many2one(
        comodel_name="res.partner", string="Vendor", required=True, index=True, ondelete="cascade"
    )
    day = fields.Date(required=True, help="The day at the hour of the vendor.")
    kind = fields.Selection(selection=KINDS, required=True)
    res_id = fields.Integer(
        string="Record", default=0, required=True,
        help="The live of a « Watch », the product of a WhatsApp contact; 0 otherwise.",
    )
    count = fields.Integer(default=0, required=True)

    _unique_count = models.UniqueIndex("(vendor_id, day, kind, res_id)", "One count per vendor, day, kind and record.")

    # === COUNT === #

    @api.model
    def _ocd_add(self, vendor, kind, res_id=0):
        """Count one tap of `kind` for `vendor` today (their day), kept in memory and written with
        the others every few seconds."""
        if not vendor:
            return
        vendor = vendor.sudo()
        local = tools.to_tz(fields.Datetime.now(), vendor._ocd_tz_name())
        key = (self.env.cr.dbname, vendor.id, local.date().isoformat(), kind, int(res_id or 0))
        with _counts_lock:
            _counts[key] += 1
            due = time.monotonic() - _counts_written[0] >= COUNT_SECONDS
        if due or odoo_module.current_test:
            self._ocd_write_counts()

    @api.model
    def _ocd_write_counts(self):
        """Write the taps counted by this worker: in a transaction of their own that waits for the
        other workers a moment instead of failing (READ COMMITTED), never with the page."""
        dbname = self.env.cr.dbname
        with _counts_lock:
            counts = {key[1:]: count for key, count in _counts.items() if key[0] == dbname}
            for key in counts:
                del _counts[(dbname, *key)]
            _counts_written[0] = time.monotonic()
        if not counts:
            return
        try:
            if odoo_module.current_test:
                _add_counts(self.env.cr, counts)  # the tests run in one transaction
            else:
                with self.env.registry.cursor() as cr:
                    cr.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                    _add_counts(cr, counts)
        except psycopg2.Error:
            # An indication for the vendor: it never breaks a page
            _logger.warning("OCD Live: figures of the vendors not written", exc_info=True)
            return
        self.invalidate_model()

    # === READ === #

    @api.model
    def _ocd_totals(self, vendor, kind, start, end, by_record=False):
        """The taps of `kind` for `vendor` from the day `start` to the day `end` (both included):
        a number, or {record: count} with `by_record`."""
        domain = [("vendor_id", "=", vendor.id), ("kind", "=", kind), ("day", ">=", start), ("day", "<=", end)]
        groups = self.sudo()._read_group(domain, ["res_id"] if by_record else [], ["count:sum"])
        if by_record:
            return {res_id: total for res_id, total in groups}
        return (groups[0][0] or 0) if groups else 0

    @api.model
    def _ocd_record_totals(self, vendor, kind, res_ids):
        """{record: taps} of `kind` for the records `res_ids` of `vendor`, all days."""
        if not res_ids:
            return {}
        groups = self.sudo()._read_group(
            [("vendor_id", "=", vendor.id), ("kind", "=", kind), ("res_id", "in", list(res_ids))],
            ["res_id"], ["count:sum"],
        )
        return dict(groups)

    @api.autovacuum
    def _gc_old_counts(self):
        limit = date.today() - timedelta(days=KEPT_DAYS)
        self.sudo().search([("day", "<", limit)]).unlink()

