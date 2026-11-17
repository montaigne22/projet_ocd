"""« My team » of the vendor (chantier 22, A.9 of the plan of « My products », design
EquipeDuVendeur): the people who hold the stores, their store, whether they came; add one (name,
WhatsApp, store) and send her link, send it again, change her store, remove her."""
import re
from urllib.parse import quote

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common


class OcdVendorTeam(http.Controller):

    def _vendor(self):
        return common.current_vendor()

    def _own_member(self, vendor, member_id):
        member = request.env["ocd.vendor.member"].sudo().browse(member_id).exists()
        if not member or member.vendor_id != vendor or not member.active:
            raise request.not_found()
        return member

    def _places(self, vendor):
        """The stores a person can hold: the places of the vendor not refused."""
        return request.env["ocd.vendor.place"].sudo().search(
            [("vendor_id", "=", vendor.id), ("state", "!=", "refused")], order="sequence, id"
        )

    def _visit_line(self, member):
        env = request.env
        if not member.last_visit:
            return ""
        when = common.to_viewer(member.last_visit)
        if when.date() == common.to_viewer(fields.Datetime.now()).date():
            return env._("Last visit: today, %s", when.strftime("%H:%M"))
        return env._("Last visit: %s", tools.day_text(env, when.date(), "d MMM"))

    def _share_url(self, member):
        """The link of her space, sent by the vendor from their own WhatsApp (when the message of
        OCD Live cannot leave)."""
        phone = re.sub(r"\D", "", member.phone or "")
        text = request.env._("Hello %(name)s, here is your space for %(store)s on OCD Live: %(url)s",
                             name=member._ocd_first_name(), store=member.place_id.name, url=member._ocd_url())
        return f"https://wa.me/{phone}?text={quote(text)}"

    def _render(self, vendor, error=None, form=None, message=None, share=None):
        env = request.env
        company = vendor.company_id or env.company
        members = env["ocd.vendor.member"].sudo().search([("vendor_id", "=", vendor.id)])
        places = self._places(vendor)
        allowed = vendor._ocd_team_allowed()
        labels = {"active": env._("Active"), "waiting": env._("Not come yet"), "paused": env._("Paused")}
        rows = [{
            "member": member,
            "initials": common.initials(member.name),
            "line": " · ".join(part for part in (member.phone, member.place_id.name) if part),
            "state": member.state,
            "state_label": labels[member.state],
            "visit": self._visit_line(member),
        } for member in members]
        business = vendor._ocd_business()
        if not business:
            business_line = False
        elif company.ocd_business_offered_all:
            business_line = env._("offered during the launch.")
        else:
            business_line = env._("until %s.", tools.day_text(env, vendor.ocd_business_until, "d MMMM yyyy"))
        stock_here = vendor._ocd_stock_in_places()
        if not business:
            blocked = env._("The team comes with OCD Business: write to OCD Live to have it.")
        elif not stock_here:
            blocked = env._("Your pieces are kept in the stock of OCD Live: your stores have no stock to hold.")
        elif not places:
            blocked = env._("Add your store first: each person holds one of your stores.")
        elif len(members) >= allowed:
            blocked = env._("%s people at most in a team: remove someone to add another one.", allowed)
        else:
            blocked = False
        form = form or {}
        country = vendor.country_id or common.default_country()
        return request.render("ocd_live_shop.vendor_team", common.page_values(
            False,
            space_page="team",
            back="/ocd/espace/moi",
            back_label=env._("Back to my space"),
            header_title=env._("My team"),
            vendor=vendor,
            rows=rows,
            places=places,
            business_line=business_line,
            paused=bool(members) and not business,
            blocked=blocked,
            add_places=not places and business and stock_here,
            count_line=(env._("1 person out of %s.", allowed) if len(members) == 1
                        else env._("%(count)s people out of %(max)s.", count=len(members), max=allowed)) if allowed else "",
            error=error,
            message=message,
            share=share,
            form_name=form.get("name", ""),
            phone_value=form.get("phone", ""),
            form_place=int(form.get("place_id") or 0) or (places[:1].id if len(places) == 1 else 0),
            dial_rows=common.dial_rows(form.get("country") or country),
        ))

    @http.route("/ocd/espace/moi/equipe", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def team(self, ajoute=None, lien=None, retire=None, change=None, **kwargs):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        message, share = None, None
        member = env["ocd.vendor.member"].sudo().browse(int(ajoute or lien or 0)).exists() if (ajoute or lien) else None
        if member and member.vendor_id == vendor and member.active:
            sent = bool(member.invited_at) and member.invited_at >= fields.Datetime.subtract(fields.Datetime.now(), minutes=2)
            if sent:
                message = env._("%s is in your team: her link left on WhatsApp.", member._ocd_first_name()) if ajoute \
                    else env._("Her link left on WhatsApp.")
            else:
                message = env._("%s is in your team.", member._ocd_first_name()) if ajoute else None
                share = {"url": self._share_url(member), "name": member._ocd_first_name()}
        elif retire:
            message = env._("Removed: she no longer opens the space of the store.")
        elif change:
            message = env._("Saved.")
        return self._render(vendor, message=message, share=share)

    @http.route("/ocd/espace/moi/equipe", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def team_add(self, name=None, phone=None, country_id=None, place_id=None, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        country = env["res.country"].sudo().browse(int(country_id or 0)).exists() or vendor.country_id or common.default_country()
        form = {"name": common.clean_text(name), "phone": phone or "", "place_id": place_id, "country": country}
        place = self._places(vendor).filtered(lambda p: str(p.id) == str(place_id))[:1]
        try:
            number = common.normalize_phone(country, phone)
            if not number:
                raise UserError(common.phone_error(country))
            member = env["ocd.vendor.member"].sudo()._ocd_add(vendor, form["name"], number, place)
        except (UserError, ValidationError) as exc:
            return self._render(vendor, error=exc.args[0], form=form)
        return request.redirect(f"/ocd/espace/moi/equipe?ajoute={member.id}")

    @http.route("/ocd/espace/moi/equipe/<int:member_id>/lien", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def team_link(self, member_id, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        member = self._own_member(vendor, member_id)
        if not member.partner_id._ocd_may_send_link():
            return self._render(vendor, error=request.env._("A link left less than a minute ago: wait a little."))
        member._ocd_send_link()
        return request.redirect(f"/ocd/espace/moi/equipe?lien={member.id}")

    @http.route("/ocd/espace/moi/equipe/<int:member_id>/retirer", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def team_remove(self, member_id, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        self._own_member(vendor, member_id)._ocd_remove()
        return request.redirect("/ocd/espace/moi/equipe?retire=1")

    @http.route("/ocd/espace/moi/equipe/<int:member_id>/magasin", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def team_move(self, member_id, place_id=None, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        member = self._own_member(vendor, member_id)
        place = self._places(vendor).filtered(lambda p: str(p.id) == str(place_id))[:1]
        try:
            member._ocd_move(place)
        except UserError as exc:
            return self._render(vendor, error=exc.args[0])
        return request.redirect("/ocd/espace/moi/equipe?change=1")
