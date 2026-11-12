from odoo import http
from odoo.http import request

from .. import tools
from . import common


class OcdLiveRemote(http.Controller):
    """« Join my live »: the page of the vendor of a remote live, whose link comes in the
    invitation 15 minutes before (and in the space of the vendor): the steps to join the account
    of OCD Live as a guest, « I am ready », « I have a problem », the host and how to call them.
    The team sees what the vendor says in the form of the live and in the control room."""

    def _join_booking(self, booking_id, token=None):
        """The remote live of the link (its secret), or of the vendor of this browser."""
        booking = request.env["ocd.live.booking"].sudo().browse(booking_id).exists()
        if not booking or booking.mode != "remote" or booking.state not in ("confirmed", "done"):
            raise request.not_found()
        vendor = common.current_vendor()
        if not ((vendor and booking.partner_id == vendor) or (token and booking._ocd_join_check(token))):
            raise request.not_found()
        return booking

    def _join_values(self, booking, saved=None, error=None):
        env = request.env
        now = common.now()
        tz_name = common.viewer_tz()
        local = tools.to_tz(booking.start_datetime, tz_name)
        today = tools.to_tz(now, tz_name).date()
        hour = f"{local:%H:%M}"
        minutes = int((booking.start_datetime - now).total_seconds() // 60)
        if now >= booking.end_datetime or booking.state == "done":
            phase = "ended"
            title = env._("Your live is over")
            lead = env._("Thank you! The replay comes in your boutique.")
        elif now >= booking.start_datetime:
            phase = "live"
            title = env._("Your live started at %s", hour)
            lead = env._("Join it now: accept the invitation of OCD Live.")
        else:
            phase = "coming"
            if local.date() == today:
                title = env._("Your live starts at %s", hour)
            else:
                title = env._("Your live: %(day)s at %(hour)s", day=common.day_text(local.date(), "EEEE d MMMM"), hour=hour)
            if minutes <= 60:
                lead = env._("In %s min · remote, with OCD Live", max(minutes, 1))
            else:
                lead = env._("Remote, with OCD Live. You receive the link of this page 15 minutes before.")
        account = booking.account_id
        # The live of the account, where the invitation comes (else the link given to the live)
        watch_url = account.live_url or booking._ocd_watch_url()
        platform = account.platform_id.name or env["ocd.live.platform"].sudo()._ocd_for_url(watch_url).name or ""
        host = booking.animatrice_id
        host_phone = booking._ocd_host_phone() or common.company().phone
        token = booking._ocd_join_token()
        problems = booking._fields["ocd_vendor_problem"]._description_selection(env)
        return common.page_values(
            False,
            back="/ocd/espace/moi",
            back_label=env._("My space"),
            header_title=env._("Join my live"),
            booking=booking,
            vendor=booking.partner_id,
            phase=phase,
            title=title,
            lead=lead,
            account=account,
            platform=platform,
            watch_url=watch_url,
            handle=booking.partner_id.ocd_live_handle or "",
            host_name=host.name or env._("The team of OCD Live"),
            host_is_team=not host,
            call_url=f"tel:{host_phone}" if host_phone else False,
            whatsapp_url=tools.whatsapp_url(host_phone, env._(
                "Hello, this is %(vendor)s, for my live of %(hour)s.", vendor=booking.partner_id.name, hour=hour,
            )),
            action_base=f"/ocd/live/{booking.id}/rejoindre/{token}",
            problems=problems,
            saved=saved,
            error=error,
        )

    @http.route(
        ["/ocd/live/<int:booking_id>/rejoindre", "/ocd/live/<int:booking_id>/rejoindre/<string:token>"],
        type="http", auth="public", website=True, sitemap=False, methods=["GET"],
    )
    def join(self, booking_id, token=None, ok=None, **kwargs):
        booking = self._join_booking(booking_id, token)
        return request.render("ocd_live.join", self._join_values(booking, saved=ok))

    @http.route(
        "/ocd/live/<int:booking_id>/rejoindre/<string:token>/pret",
        type="http", auth="public", website=True, sitemap=False, methods=["POST"],
    )
    def join_ready(self, booking_id, token, **post):
        booking = self._join_booking(booking_id, token)
        if booking.state == "confirmed" and booking.end_datetime > common.now():
            booking._ocd_vendor_says_ready()
        return request.redirect(f"/ocd/live/{booking.id}/rejoindre/{token}?ok=ready")

    @http.route(
        "/ocd/live/<int:booking_id>/rejoindre/<string:token>/probleme",
        type="http", auth="public", website=True, sitemap=False, methods=["POST"],
    )
    def join_problem(self, booking_id, token, problem=None, note=None, **post):
        booking = self._join_booking(booking_id, token)
        if booking.state == "confirmed" and booking.end_datetime > common.now():
            booking._ocd_vendor_says_problem(problem, common.clean_text(note, 300))
        return request.redirect(f"/ocd/live/{booking.id}/rejoindre/{token}?ok=problem")

    @http.route(
        "/ocd/live/<int:booking_id>/rejoindre/<string:token>/compte",
        type="http", auth="public", website=True, sitemap=False, methods=["POST"],
    )
    def join_handle(self, booking_id, token, handle=None, **post):
        """The vendor gives their name on the platform: the host invites this account."""
        booking = self._join_booking(booking_id, token)
        handle = common.clean_text(handle, 60)
        if not handle:
            return request.render("ocd_live.join", self._join_values(
                booking, error=request.env._("Write your name on the platform, for example @awa.gateaux."),
            ))
        if not handle.startswith("@") and " " not in handle:
            handle = f"@{handle}"
        booking.partner_id.ocd_live_handle = handle
        booking.message_post(body=request.env._("Name of the vendor on the platform: %s", handle))
        return request.redirect(f"/ocd/live/{booking.id}/rejoindre/{token}?ok=handle")
