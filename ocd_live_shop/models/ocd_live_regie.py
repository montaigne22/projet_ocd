from datetime import datetime, time, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount

from odoo.addons.ocd_live.tools import day_text

PLATFORMS = (
    ("tiktok.com", "TikTok"),
    ("facebook.com", "Facebook"),
    ("fb.watch", "Facebook"),
    ("instagram.com", "Instagram"),
    ("youtube.com", "YouTube"),
    ("youtu.be", "YouTube"),
)


class OcdLiveRegie(models.AbstractModel):
    """Live control room of the team, as in the validated design (Regie): the live of now, its
    figures, the product the vendor shows (put on the boutique at once), the moments of the
    replay and the replay link to publish after the live."""

    _name = "ocd.live.regie"
    _description = "OCD Live Control Room"

    @api.model
    def _ocd_find_live(self, booking_id=False):
        """The live asked, else the live of now, else the next live of today, else the last one."""
        Booking = self.env["ocd.live.booking"]
        if booking_id:
            booking = Booking.browse(booking_id).exists()
            if booking:
                return booking
        company = self.env.company
        now = fields.Datetime.now()
        domain = [("company_id", "=", company.id), ("state", "in", ("confirmed", "done"))]
        live = Booking.search(domain + [("start_datetime", "<=", now), ("end_datetime", ">", now)], limit=1)
        if live:
            return live
        tz = company._ocd_tz()
        midnight = company._ocd_to_utc(tz.localize(datetime.combine(company._ocd_local_today(), time())))
        return (
            Booking.search(
                domain + [("start_datetime", ">", now), ("start_datetime", "<", midnight + timedelta(days=1))],
                order="start_datetime",
                limit=1,
            )
            or Booking.search(domain + [("start_datetime", "<=", now)], order="start_datetime desc", limit=1)
        )

    @api.model
    def get_regie_data(self, booking_id=False):
        booking = self._ocd_find_live(booking_id)
        if not booking:
            return {"booking_id": False}
        company = booking.company_id
        now = fields.Datetime.now()
        start = company._ocd_to_local(booking.start_datetime)
        end = company._ocd_to_local(booking.end_datetime)
        vendor = booking.partner_id
        city = vendor.city or vendor.country_id.name or ""
        place = (
            self.env._("remote, %s", city) if booking.mode == "remote" and city
            else self.env._("remote") if booking.mode == "remote"
            else self.env._("at the studio")
        )
        line = [part for part in (vendor.ocd_category_id.name, place, booking.animatrice_id.name) if part]
        orders = self._ocd_live_orders(booking)
        currency = company.currency_id
        total = sum(
            order.currency_id._convert(order.amount_total, currency, company, order.date_order) for order in orders
        )
        if booking.start_datetime <= now < booking.end_datetime and booking.state == "confirmed":
            status = "live"
        elif booking.start_datetime > now:
            status = "coming"
        else:
            status = "ended"
        base_url = booking.get_base_url().split("://", 1)[-1].rstrip("/")
        return {
            "booking_id": booking.id,
            "status": status,
            "pager": self.env._("Live now: %s", vendor.name) if status == "live" else vendor.name,
            "when": self.env._(
                "%(day)s · %(start)s – %(end)s, time of %(city)s",
                day=day_text(self.env, start.date(), "EEE d MMM"),
                start=start.strftime("%H:%M"),
                end=end.strftime("%H:%M"),
                city=company.ocd_studio_city or "Lomé",
            ),
            "start": fields.Datetime.to_string(booking.start_datetime),
            "end": fields.Datetime.to_string(booking.end_datetime),
            "now": fields.Datetime.to_string(now),
            "vendor": vendor.name,
            "line": " · ".join(line),
            "visits": booking.ocd_visit_count,
            "orders": self.env._(
                "%(count)s · %(amount)s", count=len(orders), amount=format_amount(self.env, total, currency)
            ),
            "orders_action": {
                "type": "ir.actions.act_window",
                "name": self.env._("Orders during the live"),
                "res_model": "sale.order",
                "views": [[False, "list"], [False, "form"]],
                "domain": [("id", "in", orders.ids)],
                "target": "current",
            },
            "live_url": booking.live_url or "",
            "platform": self._ocd_platform(booking.live_url),
            "banner_title": " · ".join(part for part in (vendor.name, vendor.ocd_category_id.name, city) if part),
            "banner_sub": self.env._("Order on OCD Live: %s", f"{base_url}/ocd/boutique/{vendor.id}"),
            "sold_by_ocd": vendor.ocd_sale_mode == "ocd",
            "replay_url": booking.replay_url or "",
            "replay_published": booking.replay_published,
            "products": [self._ocd_product_tile(booking, product) for product in booking.vendor_product_ids],
            "moments": [
                {"id": moment.id, "time": moment.offset_label, "name": moment.product_tmpl_id.name}
                for moment in booking.moment_ids.sorted("offset_seconds")
            ],
            "can_show": booking.state in ("confirmed", "done"),
        }

    @api.model
    def _ocd_platform(self, url):
        url = (url or "").lower()
        return next((name for domain, name in PLATFORMS if domain in url), "")

    @api.model
    def _ocd_live_orders(self, booking):
        """Orders of the products of the vendor received during the live."""
        # sudo: the totals of the orders of the live are shown to the team of the control room
        lines = self.env["sale.order.line"].sudo().search([
            ("product_id.product_tmpl_id.ocd_vendor_id", "=", booking.partner_id.id),
            ("order_id.state", "=", "sale"),
            ("order_id.date_order", ">=", booking.start_datetime),
            ("order_id.date_order", "<", booking.end_datetime),
        ])
        return lines.order_id

    @api.model
    def _ocd_product_tile(self, booking, product):
        stock = ""
        if product.is_storable:
            quantity = int(product.qty_available)
            stock = self.env._("%s in stock", quantity) if quantity > 0 else self.env._("sold out")
        return {
            "id": product.id,
            "name": product.name,
            "price": format_amount(self.env, product.list_price, product.currency_id),
            "stock": stock,
            "image": f"/web/image/product.template/{product.id}/image_128",
            "shown": product == booking.current_product_tmpl_id,
        }

    @api.model
    def ocd_show_product(self, booking_id, product_id):
        booking = self.env["ocd.live.booking"].browse(booking_id).exists()
        product = self.env["product.template"].browse(product_id).exists()
        if not booking or not product:
            raise UserError(self.env._("This live or this product no longer exists."))
        booking._ocd_show_product(product)
        return True

    @api.model
    def ocd_publish_replay(self, booking_id, url):
        booking = self.env["ocd.live.booking"].browse(booking_id).exists()
        if not booking:
            raise UserError(self.env._("This live no longer exists."))
        booking.replay_url = (url or "").strip()
        booking.action_publish_replay()
        return True
