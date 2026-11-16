import re
import time
import uuid

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import BinaryBytes

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common

from .. import share_image
from ..models.ocd_vendor_place import POSITION_MAX_METERS
from .vendor_share import drawn, short_link
from .vendor_products import FORM_TOKEN, keep_photo, kept_photo, kept_values, pending_photos, read_photo

# An hour typed in a form: "08:00", "8:00", "19:30"
HOUR = re.compile(r"(\d{1,2}):(\d{2})")
# The sizes of the photo of a front
PHOTO_SIZES = (128, 256, 512, 1024)
# What a customer does with a store, counted for its vendor; once per visitor every 10 minutes
TAP_KINDS = ("itinerary", "call", "whatsapp")
TAP_EVERY = 600


def parse_hour(text):
    """8.5 for "08:30", 24.0 for "24:00"; None when it is not an hour of the day."""
    match = HOUR.fullmatch((text or "").strip())
    if not match:
        return None
    hours, minutes = int(match.group(1)), int(match.group(2))
    if minutes > 59 or hours > 24 or (hours == 24 and minutes):
        return None
    return hours + minutes / 60


def place_photo_url(place, size=512):
    """The front of a place, for its vendor and, once shown, for the customers; its address
    changes with the photo."""
    if not place or not place.photo:
        return False
    stamp = place.write_date.strftime("%Y%m%d%H%M%S") if place.write_date else "0"
    return f"/ocd/magasin/{place.id}/photo?size={size}&unique={stamp}"


class OcdVendorPlaces(http.Controller):
    """My stores (designs MesMagasins and MonMagasin, chantier 17): where the customers find the
    vendor. A store is checked by the team before it is shown; a home shows its district only."""

    def _vendor(self):
        return common.current_vendor()

    def _own_place(self, vendor, place_id):
        place = request.env["ocd.vendor.place"].sudo().browse(place_id).exists()
        if not place or place.vendor_id != vendor or not place.active:
            raise request.not_found()
        return place

    def _cities(self, vendor, place=None):
        """The cities a place can be in: those of the country of the place, else of the vendor,
        else of OCD Live; the city of the place always among them. Without any city in that
        country, the cities that have districts (where OCD Live delivers)."""
        City = request.env["res.city"].sudo()
        place_city = place.city_id if place else City
        country = (
            place_city.country_id or vendor.country_id or vendor.city_id.country_id or common.company().country_id
        )
        cities = City.search([("country_id", "=", country.id)], order="name") if country else City
        if not cities:
            districts = request.env["res.city.district"].sudo()._read_group([], ["city_id"])
            cities = City.browse([city.id for (city,) in districts]).sorted("name")
        return cities | place_city if place_city not in cities else cities

    # === THE LIST === #

    def _state(self, place):
        env = request.env
        if place.kind == "home":
            return "on", env._("Shown")
        return {
            "approved": ("on", env._("Online")),
            "to_check": ("check", env._("To check")),
            "refused": ("refused", env._("Refused")),
        }[place.state]

    def _render_list(self, vendor, saved=False):
        env = request.env
        places = env["ocd.vendor.place"].sudo().search([("vendor_id", "=", vendor.id)], order="sequence, id")
        shown = env["ocd.vendor.place"]._ocd_shown_places(vendor)
        departure = vendor._ocd_departure_place()
        taps = places._ocd_week_taps()
        rows = []
        for place in places:
            status, label = self._state(place)
            week = taps[place.id]
            visits = [
                (env._("1 itinerary") if week["itinerary"] == 1 else env._("%s itineraries", week["itinerary"])) if week["itinerary"] else "",
                (env._("1 call") if week["call"] == 1 else env._("%s calls", week["call"])) if week["call"] else "",
                (env._("1 WhatsApp message") if week["whatsapp"] == 1 else env._("%s WhatsApp messages", week["whatsapp"])) if week["whatsapp"] else "",
            ]
            visits = [visit for visit in visits if visit]
            rows.append({
                "place": place,
                "status": status,
                "status_label": label,
                "address": place._ocd_address_line() if place.kind == "store" else place._ocd_area(),
                "open": place._ocd_open_state() if place.kind == "store" and place.state == "approved" else False,
                "hours": " · ".join(place._ocd_hours_lines()) if place.kind == "store" else False,
                "visits": env._("This week: %s", ", ".join(visits)) if visits else False,
                "refusal": place._ocd_refusal_text(),
                "hidden": place.state == "approved" and place not in shown,
                "departure": place == departure,
                "photo": place_photo_url(place, 256),
                "poster": place.kind == "store" and place.state == "approved",
            })
        sends_parcels = vendor.ocd_sale_mode == "ocd" and (
            vendor.ocd_delivery_mode or common.company().ocd_default_delivery_mode
        ) in ("pickup", "vendor")
        return request.render("ocd_live_shop.vendor_places", common.page_values(
            "mes_magasins",
            space_page="places",
            back="/ocd/espace/moi",
            back_label=env._("Back to my space"),
            header_title=env._("My stores"),
            vendor=vendor,
            rows=rows,
            saved=saved,
            can_add=vendor._ocd_places_left() > 0,
            departure_choice=sends_parcels and len(places) > 1,
            departure=departure,
            places=places,
        ))

    @http.route("/ocd/espace/moi/magasins", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def places(self, enregistre=None, **kwargs):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        return self._render_list(vendor, saved=bool(enregistre))

    # === THE FORM OF A PLACE === #

    def _hour_rows(self, place, values):
        """The 7 days of the form: from what was sent, else the place, else the hours proposed."""
        env = request.env
        names = [env._("Mon."), env._("Tue."), env._("Wed."), env._("Thu."), env._("Fri."), env._("Sat."), env._("Sun.")]
        if values:
            return [{
                "day": day, "label": names[day], "open": bool(values.get(f"open_{day}")),
                "from": values.get(f"from_{day}") or "08:00", "to": values.get(f"to_{day}") or "19:00",
            } for day in range(7)]
        intervals = place._ocd_intervals() if place else common.company()._ocd_place_default_intervals()
        rows = []
        for day in range(7):
            ranges = intervals[day]
            start, end = (ranges[0][0], ranges[-1][1]) if ranges else (8.0, 19.0)
            rows.append({"day": day, "label": names[day], "open": bool(ranges),
                         "from": tools.hour_text(start), "to": tools.hour_text(end)})
        return rows

    def _render_form(self, vendor, place=None, values=None, errors=None, kept=None):
        env = request.env
        company = common.company()
        values = values or {}
        cities = self._cities(vendor, place)
        city_id = values.get("city_id") or (place.city_id.id if place else False) or (vendor.city_id.id if vendor.city_id else False)
        city = cities.filtered(lambda c: c.id == int(city_id or 0))[:1] or cities[:1]
        districts = env["res.city.district"].sudo().search([("city_id", "=", city.id)], order="name") if city else []
        kind = values.get("kind") or (place.kind if place else "store")
        return request.render("ocd_live_shop.vendor_place_form", common.page_values(
            "mon_magasin",
            space_page="places",
            back="/ocd/espace/moi/magasins",
            back_label=env._("Back to my stores"),
            header_title=env._("My stores"),
            vendor=vendor,
            place=place or False,
            kind=kind,
            name=values.get("name", place.name if place else ""),
            landmark=values.get("landmark", place.landmark if place else ""),
            phone=values.get("phone", place.phone if place else ""),
            cities=cities,
            city=city,
            districts=districts,
            district_id=int(values.get("district_id") or (place.district_id.id if place else 0) or 0),
            hours=self._hour_rows(place, values if values else None),
            closed=bool(values.get("closed")) if values else bool(place and place.closed_until),
            closed_until=values.get("closed_until") or (fields.Date.to_string(place.closed_until) if place and place.closed_until else ""),
            position_known=bool(place and place._ocd_has_position()),
            position_accuracy=place.position_accuracy if place else 0,
            current_photo=place_photo_url(place, 512) if place else False,
            kept_photo=kept_values(kept),
            form_token=(values or {}).get("form_token") or uuid.uuid4().hex,
            home_allowed=company.ocd_place_home_allowed,
            proof_required=company.ocd_place_proof_required,
            photo_px=company.ocd_vendor_photo_px or 0,
            photo_max_mb=company._ocd_vendor_photo_max_bytes() // (1024 * 1024),
            errors=errors or {},
            form_messages={
                "name": env._("Write the name of the store."),
                "district": env._("Choose the district."),
                "photo": env._("Add a photo of the front, with its sign."),
                "position": env._("Take the position inside your store."),
                "locating": env._("Looking for the position…"),
                "located": env._("Position taken, within %s m"),
                "vague": env._("The position is not precise enough (within %s m): take it again near the door or outside, in front of the store."),
                "denied": env._("Allow the position for this site in your phone, then try again."),
                "unavailable": env._("The phone did not find the position: try again in a moment, near the door."),
                "photo_big": env._("The photo is too big (%s MB at most).", company._ocd_vendor_photo_max_bytes() // (1024 * 1024)),
                "sending": env._("Sending…"),
            },
        ))

    @http.route("/ocd/espace/moi/magasins/nouveau", type="http", auth="public", website=True,
                methods=["GET", "POST"], sitemap=False)
    def place_new(self, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        if vendor._ocd_places_left() <= 0:
            return request.redirect("/ocd/espace/moi/magasins")
        if request.httprequest.method != "POST":
            return self._render_form(vendor)
        return self._save(vendor, None, post)

    @http.route("/ocd/espace/moi/magasins/<int:place_id>", type="http", auth="public", website=True,
                methods=["GET", "POST"], sitemap=False)
    def place_edit(self, place_id, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        place = self._own_place(vendor, place_id)
        if request.httprequest.method != "POST":
            return self._render_form(vendor, place)
        return self._save(vendor, place, post)

    def _save(self, vendor, place, post):
        """Check the form and save the place: (re)sent to the check of the team when needed."""
        env = request.env
        company = common.company()
        _ = env._
        errors = {}
        token = post.get("form_token") if FORM_TOKEN.fullmatch(post.get("form_token") or "") else None
        if place is None and token:
            # A second tap on a slow network: one at a time, and the second one finds the place
            # of the first
            env.cr.execute("SELECT pg_advisory_xact_lock(%s, %s)", [vendor.id, int(token[:7], 16)])
            if env["ocd.vendor.place"].sudo().with_context(active_test=False).search_count(
                [("vendor_id", "=", vendor.id), ("form_token", "=", token)], limit=1
            ):
                return request.redirect("/ocd/espace/moi/magasins?enregistre=1")
        kind = post.get("kind") if post.get("kind") in ("store", "home") else "store"
        if kind == "home" and not company.ocd_place_home_allowed:
            kind = "store"
        name = common.clean_text(post.get("name"), 80)
        if not name:
            if kind == "store":
                errors["name"] = _("Write the name of the store.")
            name = _("My home")
        cities = self._cities(vendor, place)
        city = cities.filtered(lambda c: str(c.id) == str(post.get("city_id")))[:1]
        district = env["res.city.district"].sudo().browse(
            int(post["district_id"]) if str(post.get("district_id", "")).isdigit() else 0
        ).exists()
        if not city:
            errors["district"] = _("Choose the city.")
        elif not district or district.city_id != city:
            errors["district"] = _("Choose the district.")
            district = env["res.city.district"]
        values = {
            "name": name, "kind": kind, "city_id": city.id or False, "district_id": district.id or False,
            "landmark": common.clean_text(post.get("landmark"), 120) or False,
        }
        # The position: only when the phone took it now
        taken = post.get("position_taken") == "1"
        if taken:
            try:
                latitude, longitude = float(post.get("latitude")), float(post.get("longitude"))
                accuracy = int(float(post.get("accuracy") or 0))
            except (TypeError, ValueError):
                latitude = longitude = None
                accuracy = 0
            if latitude is None or not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or not (latitude or longitude):
                errors["position"] = _("Take the position inside your store.")
            elif accuracy > POSITION_MAX_METERS:
                errors["position"] = _("The position is not precise enough (within %s m): take it again near the door or outside, in front of the store.", accuracy)
            else:
                values.update(latitude=latitude, longitude=longitude, position_accuracy=accuracy)
        # The front: sent now, or kept after an error
        data, filename, photo_error = read_photo(post.get("photo"), _("Add a photo of the front, with its sign."))
        kept = kept_photo(vendor, post.get("photo_kept")) if data is None else env["ir.attachment"]
        if photo_error:
            errors["photo"] = photo_error
        elif data is None and kept:
            data, filename = kept.raw, kept.name
        if data is not None and kind == "store":
            values["photo"] = BinaryBytes(data, filename=filename)
        # The phone, written as the customers call it
        phone = common.clean_text(post.get("phone"), 30)
        country = vendor.country_id or company.country_id
        if phone:
            normalized = common.normalize_phone(country, phone)
            if not normalized:
                errors["phone"] = common.phone_error(country)
            phone = normalized or phone
        values["phone"] = phone or False
        # The hours, day by day
        names = [_("Mon."), _("Tue."), _("Wed."), _("Thu."), _("Fri."), _("Sat."), _("Sun.")]
        intervals = {}
        for day in range(7):
            intervals[day] = []
            if not post.get(f"open_{day}"):
                continue
            start, end = parse_hour(post.get(f"from_{day}")), parse_hour(post.get(f"to_{day}"))
            if start is None or end is None or start >= end:
                errors.setdefault("hours", _("Check %s: the store opens before it closes.", names[day]))
            else:
                intervals[day] = [(start, end)]
        # Closed for a while
        closed_until = False
        if post.get("closed"):
            try:
                closed_until = fields.Date.to_date(post.get("closed_until") or "")
            except ValueError:
                closed_until = False
            if not closed_until:
                errors["closed"] = _("Choose the day the store opens again.")
            elif closed_until < company._ocd_local_today():
                errors["closed"] = _("Choose today or a later day.")
        values["closed_until"] = closed_until or False
        # What a store needs to be checked (setting)
        if kind == "store" and company.ocd_place_proof_required:
            if "photo" not in values and not (place and place.photo) and "photo" not in errors:
                errors["photo"] = _("Add a photo of the front, with its sign.")
            if not taken and not (place and place._ocd_has_position()) and "position" not in errors:
                errors["position"] = _("Take the position inside your store.")
        if errors:
            if data is not None and not kept:
                kept = keep_photo(vendor, data, filename)
            form = {**post, "kind": kind, "name": "" if errors.get("name") else name, "city_id": city.id,
                    "district_id": district.id, "phone": phone}
            return self._render_form(vendor, place, form, errors, kept)
        try:
            with env.cr.savepoint():
                Place = env["ocd.vendor.place"].sudo()
                if place is None:
                    place = Place._ocd_vendor_create(vendor, {**values, "form_token": token})
                else:
                    place._ocd_vendor_update(values)
                place._ocd_set_hours(intervals)
        except (UserError, ValidationError) as exc:
            return self._render_form(vendor, place, {**post, "kind": kind}, {"form": exc.args[0]}, kept)
        pending_photos(vendor).unlink()
        return request.redirect(f"/ocd/espace/moi/magasins?enregistre=1#lieu-{place.id}")

    @http.route("/ocd/espace/moi/magasins/<int:place_id>/retirer", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def place_remove(self, place_id, **post):
        """The vendor no longer has this place: hidden from the customers, kept for the team."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        place = self._own_place(vendor, place_id)
        place.active = False
        place.message_post(body=request.env._("Removed by the vendor."))
        if vendor.ocd_departure_place_id == place:
            vendor.sudo().ocd_departure_place_id = False
        return request.redirect("/ocd/espace/moi/magasins")

    @http.route("/ocd/espace/moi/magasins/depart", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def place_departure(self, place_id=None, **post):
        """The place the courier picks up the parcels from (A.4 of the plan)."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        place = self._own_place(vendor, int(place_id)) if str(place_id or "").isdigit() else None
        if place:
            vendor.sudo().ocd_departure_place_id = place
        return request.redirect("/ocd/espace/moi/magasins?enregistre=1")

    @http.route("/ocd/espace/<string:token>/magasins", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def places_link(self, token, **kwargs):
        """The button of a WhatsApp message to the vendor: their personal link opens their
        space on the phone, then « My stores ». (« moi » takes the route of the list.)"""
        if not common.current_vendor(token):
            return request.redirect("/ocd/connexion")
        return request.redirect("/ocd/espace/moi/magasins")

    # === THE QR POSTER OF A STORE (M.7 of the plan) === #

    @http.route("/ocd/espace/moi/magasins/<int:place_id>/affiche.jpg", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def place_poster(self, place_id, **kwargs):
        """The poster to print for a store: the text set by the team, the vendor, the store and
        the QR code of the boutique. For its vendor only: drawn when asked, kept a while."""
        vendor = self._vendor()
        if not vendor:
            raise request.not_found()
        place = self._own_place(vendor, place_id)
        if place.kind != "store":
            raise request.not_found()
        env = request.env
        company = common.company()
        url = request.httprequest.url_root.rstrip("/") + f"/ocd/boutique/{vendor.id}"
        name = place.name if place.name and place.name.strip().casefold() != (vendor.name or "").strip().casefold() else ""
        values = {
            "headline": company.ocd_place_poster_text or env._("Order online too, delivered to your door"),
            "vendor": vendor.name,
            "place": " · ".join(part for part in (name, place._ocd_area()) if part),
            "scan": env._("Scan with the camera of your phone"),
            "link": short_link(url),
            "url": url,
        }
        data = drawn(("poster", tuple(sorted(values.items())), env.lang or ""), lambda: share_image.poster(values))
        return request.make_response(data, headers=[
            ("Content-Type", "image/jpeg"),
            ("Content-Disposition", 'inline; filename="affiche-qr.jpg"'),
            ("Cache-Control", "private, max-age=600"),
        ])

    # === THE PHOTO OF A FRONT === #

    @http.route("/ocd/magasin/<int:place_id>/photo", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def place_photo(self, place_id, size=None, unique=None, **kwargs):
        """The front of a store: public once the customers see the store, else to its vendor."""
        Place = request.env["ocd.vendor.place"].sudo()
        place = Place.browse(place_id).exists()
        if not place or not place.photo or place.kind != "store":
            raise request.not_found()
        shown = place in Place._ocd_shown_places(place.vendor_id)
        if not shown and self._vendor() != place.vendor_id:
            raise request.not_found()
        size = int(size) if str(size or "").isdigit() and int(size) in PHOTO_SIZES else 512
        stream = request.env["ir.binary"]._get_image_stream_from(place, "photo", width=size, height=size)
        response = stream.get_response(immutable=bool(unique))
        if not shown:
            response.headers["Cache-Control"] = response.headers.get("Cache-Control", "").replace("public", "private")
        return response

    # === THE VISITS OF A STORE === #

    @http.route("/ocd/magasin/<int:place_id>/visite/<string:kind>", type="http", auth="public", website=True,
                methods=["POST"], csrf=False, sitemap=False)
    def place_tap(self, place_id, kind, **kwargs):
        """A customer asked for the itinerary of a store, called or wrote to it (a beacon of the
        boutique: no form, so no token; it only counts). Once per place, kind and visitor every
        10 minutes."""
        Place = request.env["ocd.vendor.place"].sudo()
        place = Place.browse(place_id).exists()
        if place and kind in TAP_KINDS and place in Place._ocd_shown_places(place.vendor_id):
            key, now = f"{place.id}:{kind}", time.time()
            seen = {k: at for k, at in (request.session.get("ocd_place_taps") or {}).items() if now - at < TAP_EVERY}
            if key not in seen:
                seen[key] = now
                request.env["ocd.vendor.place.tap"].sudo().create({"place_id": place.id, "kind": kind})
            request.session["ocd_place_taps"] = seen
        return request.make_response("", status=204)
