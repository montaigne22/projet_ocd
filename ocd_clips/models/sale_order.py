"""The sales that come from a clip (design ClipsAutomatiques, « Des chiffres honnêtes »): a visit
by the short link of a clip is kept in the session of the phone 7 days; the cart remembers the
clips visited, and when the order is confirmed, the lines of the product of a clip visited in the
7 days before are noted with it. As for the lives (ocd_live_shop, vendor_figures.py)."""
from datetime import datetime, timedelta

from odoo import fields, models
from odoo.http import request

# A sale counts for a clip when the order comes this long after the visit by its link
CLIP_SALE_DAYS = 7
# The session keeps the visits of the last clips only
SESSION_CLIPS = 30
SESSION_KEY = "ocd_clip_visits"


def visits_kept(visits, now=None):
    """The visits {clip id: ISO datetime} still counting: 7 days, the last ones."""
    now = now or fields.Datetime.now()
    kept = {}
    for clip_id, when in (visits or {}).items():
        try:
            moment = datetime.fromisoformat(when)
        except (TypeError, ValueError):
            continue
        if now - moment <= timedelta(days=CLIP_SALE_DAYS):
            kept[str(clip_id)] = moment.isoformat(timespec="seconds")
    return dict(sorted(kept.items(), key=lambda item: item[1])[-SESSION_CLIPS:])


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ocd_clip_visits = fields.Json(
        string="Clips Visited", copy=False, readonly=True,
        help="The clips whose short link the customer opened, with the hour of the visit: the lines of "
        "their product count for the clip when the order comes in the 7 days after.",
    )

    def _ocd_note_clips(self, visits):
        """The cart remembers the clips visited `visits` ({clip id: ISO datetime})."""
        for order in self.filtered(lambda order: order.state == "draft"):
            merged = visits_kept({**(order.ocd_clip_visits or {}), **(visits or {})})
            if merged != (order.ocd_clip_visits or {}):
                order.sudo().ocd_clip_visits = merged

    def _verify_cart_after_update(self):
        """The clips visited on this phone go with the cart."""
        super()._verify_cart_after_update()
        if request and request.session.get(SESSION_KEY):
            self._ocd_note_clips(request.session[SESSION_KEY])

    def _action_confirm(self):
        result = super()._action_confirm()
        self._ocd_note_clip_lines()
        return result

    def _ocd_note_clip_lines(self):
        """Each line of a product counts for its clip visited in the 7 days before the order (the
        last visit when there are several)."""
        Clip = self.env["ocd.live.clip"].sudo()
        for order in self.sudo().filtered("ocd_clip_visits"):
            visits = visits_kept(order.ocd_clip_visits, order.date_order or fields.Datetime.now())
            clips = Clip.browse([int(clip_id) for clip_id in visits]).exists()
            for line in order.order_line.filtered(lambda line: line.product_id and not line.ocd_clip_id):
                matching = clips.filtered(lambda clip: clip.product_tmpl_id == line.product_id.product_tmpl_id)
                if matching:
                    line.ocd_clip_id = max(matching, key=lambda clip: visits[str(clip.id)])


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ocd_clip_id = fields.Many2one(
        comodel_name="ocd.live.clip", string="Sold By The Clip", copy=False, readonly=True,
        index="btree_not_null", ondelete="set null",
        help="The customer opened the short link of this clip in the 7 days before the order.",
    )
