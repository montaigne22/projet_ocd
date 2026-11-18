"""The events of an organiser in their space (design OcdTickets), the same as for their contests of
OCD Vote: the tickets sold, the money collected, their share, the entries; their controllers."""
from urllib.parse import urlencode

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common
from odoo.addons.ocd_vote.controllers.organizer import LOGIN, OcdVoteOrganizer

EVENT = "/vote/organisateur/evenement"


class OcdTicketsOrganizer(OcdVoteOrganizer):

    @http.route()
    def home(self, **kwargs):
        """Override of `ocd_vote`: their contests and their events; straight to the only one."""
        organizer = self._organizer()
        if not organizer:
            return request.redirect(LOGIN)
        events = self._events(organizer)
        contests = organizer.ocd_vote_contest_ids.filtered(lambda contest: contest.state != "cancelled")
        if len(events) == 1 and not contests:
            return request.redirect(f"{EVENT}/{events.id}")
        if events:
            return self._page("ocd_vote.organizer_home", back="/billets",
                              header_title=request.env._("My contests and events"),
                              organizer=organizer, contests=contests, events=events)
        return super().home(**kwargs)

    def _event_page(self, template, **values):
        """A page of their events: « Tickets » lit in the menu."""
        return request.render(template, common.page_values(
            False,
            nav="tickets",
            header_link={"href": "/vote/organisateur/deconnexion", "post": True, "label": request.env._("Log out")},
            **values,
        ))

    def _events(self, organizer):
        return organizer.sudo().ocd_ticket_event_ids.filtered(
            lambda event: event.ocd_ticketing and event.ocd_state != "cancelled"
        ).sorted("date_begin", reverse=True)

    def _event(self, organizer, event_id):
        event = request.env["event.event"].sudo().browse(event_id).exists()
        if not event or not event.ocd_ticketing or event.ocd_organizer_id != organizer:
            raise request.not_found()
        return event

    def _event_steps(self, event):
        env = request.env
        now = common.now()
        on_sale = event.ocd_state == "approved"
        steps = [
            (event.ocd_state != "draft", env._("Event sent")),
            (on_sale, env._("Checked by OCD Live")),
            (on_sale, env._("On sale")),
            (on_sale and now >= event.date_begin, env._("The evening: the entries")),
            (event.ocd_payout_state == "paid",
             env._("Your share paid: %s", event.ocd_payout_reference or "-") if event.ocd_payout_state == "paid"
             else env._("Your share paid 3 days after the event")),
        ]
        return [{"done": done, "label": label, "index": index + 1} for index, (done, label) in enumerate(steps)]

    @http.route(f"{EVENT}/<int:event_id>", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def organizer_event(self, event_id, envoye=None, erreur=None, **kwargs):
        organizer = self._organizer()
        if not organizer:
            return request.redirect(LOGIN)
        event = self._event(organizer, event_id)
        env = request.env
        rows = []
        for ticket in event.event_ticket_ids.sorted("sequence"):
            registrations = ticket.registration_ids.filtered(
                lambda registration: registration.state in ("open", "done") and registration.ocd_refund_state == "none")
            amount = sum(registrations.mapped("ocd_amount_company"))
            seats = ticket.seats_max
            rows.append({
                "ticket": ticket,
                "count": f"{event._ocd_number(len(registrations))} / {event._ocd_number(seats)}" if seats
                else event._ocd_number(len(registrations)),
                "width": min(round(len(registrations) * 100 / seats), 100) if seats else 0,
                "amount": event._ocd_money(amount),
            })
        state_label = dict(event._fields["ocd_state"]._description_selection(env))[event.ocd_state]
        if event.ocd_state == "approved" and event._ocd_passed():
            state_label = env._("Passed")
        seats = event.seats_max if event.seats_limited else sum(event.event_ticket_ids.mapped("seats_max"))
        number = common.company().phone or ""
        return self._event_page(
            "ocd_tickets.organizer_event",
            back="/vote/organisateur",
            header_title=env._("My event"),
            event=event,
            state_label=state_label,
            steps=self._event_steps(event),
            tiles=[
                (env._("Tickets sold"), event._ocd_number(event.ocd_sold_count),
                 env._("of %s", event._ocd_number(seats)) if seats else ""),
                (env._("Collected"), event._ocd_money(event.ocd_amount_total),
                 env._("of which %s during the lives", event._ocd_money(event.ocd_live_amount))
                 if event.ocd_live_amount else env._("with the payment of OCD Live")),
                (env._("Your share (%s %%)", round(event.ocd_organizer_share)), event._ocd_money(event.ocd_organizer_amount),
                 env._("paid after the event")),
                (env._("Entered"), event._ocd_number(event.ocd_entered_count), env._("the evening itself")),
            ],
            rows=rows,
            share_url=request.httprequest.url_root.rstrip("/") + event._ocd_public_path(),
            live_url=tools.whatsapp_url(number, env._(
                "Hello, I want to sell the tickets of %s during a live of OCD Live.", event.name)) if number else False,
            message=env._("Sent: the team checks your event and writes to you on WhatsApp.") if envoye else None,
            error=erreur,
        )

    @http.route(f"{EVENT}/<int:event_id>/envoyer", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def organizer_event_send(self, event_id, **post):
        organizer = self._organizer()
        if not organizer:
            return request.redirect(LOGIN)
        event = self._event(organizer, event_id)
        try:
            event.action_ocd_send_to_check()
        except UserError as exc:
            return request.redirect(f"{EVENT}/{event.id}?{_query('erreur', exc.args[0])}")
        return request.redirect(f"{EVENT}/{event.id}?envoye=1")

    # === THE CONTROLLERS === #

    def _render_controllers(self, event, error=None, values=None, added=None):
        env = request.env
        controls = event.ocd_controller_ids.sorted(lambda control: (control.gate or "", control.name))
        return self._event_page(
            "ocd_tickets.organizer_controllers",
            back=f"{EVENT}/{event.id}",
            header_title=env._("My controllers"),
            event=event,
            rows=[{"control": control, "line": control._ocd_line()} for control in controls],
            values=values or {},
            error=error,
            message=env._("Added: %s receives the news on WhatsApp.", added) if added else None,
            dial_rows=common.dial_rows(event.address_id.country_id or common.default_country()),
        )

    @http.route(f"{EVENT}/<int:event_id>/controleurs", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def organizer_controllers(self, event_id, ajoute=None, **kwargs):
        organizer = self._organizer()
        if not organizer:
            return request.redirect(LOGIN)
        return self._render_controllers(self._event(organizer, event_id), added=ajoute)

    @http.route(f"{EVENT}/<int:event_id>/controleurs", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def organizer_controller_add(self, event_id, name=None, phone=None, country_id=None, gate=None, can_sell=None,
                                 **post):
        organizer = self._organizer()
        if not organizer:
            return request.redirect(LOGIN)
        event = self._event(organizer, event_id)
        env = request.env
        values = {"name": name, "phone": phone, "gate": gate, "can_sell": can_sell, "country_id": country_id}
        name = common.clean_text(name, 60)
        if not name:
            return self._render_controllers(event, error=env._("Write the name."), values=values)
        country = env["res.country"].sudo().browse(int(country_id or 0)).exists() or common.default_country()
        number = common.normalize_phone(country, phone)
        if not number:
            return self._render_controllers(event, error=common.phone_error(country), values=values)
        partner = env["ocd.vendor.follower"].sudo()._ocd_contact(number)
        if partner.name == number:
            partner.name = name
        Controller = env["ocd.ticket.controller"].sudo().with_context(active_test=False)
        control = Controller.search([("event_id", "=", event.id), ("partner_id", "=", partner.id)], limit=1)
        values = {"name": name, "gate": common.clean_text(gate, 30), "can_sell": bool(can_sell) and event.ocd_door_sale,
                  "active": True}
        if control:
            control.write(values)
        else:
            control = Controller.create({**values, "event_id": event.id, "partner_id": partner.id})
        control._ocd_tell_added()
        return request.redirect(f"{EVENT}/{event.id}/controleurs?{_query('ajoute', name)}")

    @http.route(f"{EVENT}/<int:event_id>/controleurs/<int:control_id>/retirer", type="http", auth="public",
                website=True, methods=["POST"], sitemap=False)
    def organizer_controller_remove(self, event_id, control_id, **post):
        organizer = self._organizer()
        if not organizer:
            return request.redirect(LOGIN)
        event = self._event(organizer, event_id)
        control = event.ocd_controller_ids.filtered(lambda control: control.id == control_id)
        control.write({"active": False})
        return request.redirect(f"{EVENT}/{event.id}/controleurs")


def _query(key, value):
    return urlencode({key: value})


def _is_known_controller():
    from .entrance import current_controller_partner
    return "ocd.ticket.controller" in request.env and bool(current_controller_partner())


# The controller changes page without reloading it, as the vendors
common.FAST_NAVIGATION_CHECKS.append(_is_known_controller)
