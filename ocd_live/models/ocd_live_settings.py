from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import format_amount, formatLang

from odoo.addons.ocd_live.models.res_company import OPEN_DAY_FIELDS

# Kinds of the settings that hold a value (the others show information or links)
VALUE_KINDS = ("check", "number", "money", "time", "date", "select", "text")


class OcdLiveSettings(models.AbstractModel):
    """Settings page of OCD Live, as in the validated design (BoParametres): the sections on
    the left, the settings of the section on the right, saved together.

    Each module adds its sections in `_ocd_sections`. A setting is a dict:
    {"kind", "key", "title", "help", ...}; its value is the field `key` of the company (or
    `field`), or is read and written by the methods named by "get" and "set". Kinds:

    - check, number (suffix, min, max), money, time (hours), date, select (options), text;
    - group (inputs) and checks (boxes): several values on one card ("fields");
    - chips, info, warn, templates: information, with an optional link ("link": action);
    - "warn_off" (check): shown in red when the protection is off.

    The managers of OCD Live change them here without being administrators of Odoo: only the
    settings of the page are written, after their checks."""

    _name = "ocd.live.settings"
    _description = "Settings Page Of OCD Live"

    # === PAGE === #

    @api.model
    def get_settings_page(self):
        self._ocd_check_manager()
        sections = sorted(self._ocd_sections(), key=lambda section: section.get("sequence", 100))
        for section in sections:
            count = len(section["items"])
            section["count"] = self.env._("1 setting") if count == 1 else self.env._("%s settings", count)
        return {
            "sections": sections,
            "values": self._ocd_read_values(sections),
        }

    @api.model
    def save_settings_page(self, values):
        """Write the changed settings `values` ({key: value}); return the page again, or the
        errors ({key: message}) without writing anything."""
        self._ocd_check_manager()
        items = {item["key"]: item for item in self._ocd_value_items()}
        errors, parsed = {}, {}
        for key, raw in (values or {}).items():
            item = items.get(key)
            if not item or item.get("readonly"):
                errors[key] = self.env._("This setting cannot be changed here.")
                continue
            try:
                parsed[key] = self._ocd_parse(item, raw)
            except UserError as error:
                errors[key] = error.args[0]
        if not errors:
            current = self._ocd_read_values(self._ocd_sections())
            errors = self._ocd_check_values({**current, **parsed})
        company_vals, setters = {}, []
        for key, value in parsed.items():
            item = items[key]
            if item.get("set"):
                setters.append((item, value))
            else:
                company_vals[item.get("field", key)] = value
        if errors:
            return {"ok": False, "errors": errors, "message": self.env._("Check the settings in red.")}
        try:
            with self.env.cr.savepoint():
                # sudo: the managers of OCD Live set the company without being administrators
                if company_vals:
                    self.env.company.sudo().write(company_vals)
                for item, value in setters:
                    getattr(self.sudo(), item["set"])(*item.get("args", []), value)
                self.env.flush_all()
        except (UserError, ValidationError) as error:
            return {"ok": False, "errors": {}, "message": error.args[0]}
        page = self.get_settings_page()
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        page.update(ok=True, saved_at=f"{now:%H:%M}")
        return page

    @api.model
    def run_settings_action(self, key):
        """The button of the setting `key` (e.g. create the rates from the delivery methods)."""
        self._ocd_check_manager()
        item = next((item for item in self._ocd_all_items() if item["key"] == key and item.get("button")), None)
        if not item:
            raise UserError(self.env._("This button is not on the settings page."))
        return getattr(self.sudo(), item["button"]["method"])() or True

    @api.model
    def _ocd_check_manager(self):
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only the managers of OCD Live change the settings."))

    # === SECTIONS === #

    @api.model
    def _ocd_sections(self):
        """Sections of the page: [{"key", "sequence", "icon", "label", "title", "items"}].
        Extended by the other modules of OCD Live."""
        return [self._ocd_section_lives(), self._ocd_section_directory(), self._ocd_section_currencies()]

    @api.model
    def _ocd_item(self, kind, key, title, help="", **extra):  # noqa: A002
        return {"kind": kind, "key": key, "title": title, "help": help, **extra}

    @api.model
    def _ocd_section_lives(self):
        _ = self.env._
        company = self.env.company
        item = self._ocd_item
        city = company.ocd_studio_city or _("the studio")
        days = zip(OPEN_DAY_FIELDS, [
            _("Mon."), _("Tue."), _("Wed."), _("Thu."), _("Fri."), _("Sat."), _("Sun."),
        ])
        packages = self.env["product.template"].sudo().search(
            [("ocd_product_kind", "=", "live_package"), ("sale_ok", "=", True)], order="list_price, id"
        )
        return {
            "key": "lives",
            "sequence": 10,
            "icon": "LV",
            "label": _("Lives and studio"),
            "title": _("Lives and studio of %s", city),
            "items": [
                item("date", "ocd_booking_open_date", _("Opening of the bookings"),
                     _("Before this date, the calendar is visible but closed."), required=True),
                item("money", "ocd_discovery_price", _("Price of a live (Discovery)"),
                     _("A live of one slot. The price of the other packages is set on each package."),
                     get="_ocd_get_discovery_price", set="_ocd_set_discovery_price",
                     suffix=company.currency_id.symbol, width=110),
                item("group", "ocd_studio_hours", _("Hours of the studio"), self._ocd_hours_text(), fields=[
                    item("time", "ocd_first_slot_hour", _("First live at"), max=23.99, before=True),
                    item("time", "ocd_slot_hours", _("Each live lasts"), min=0.25, max=8, before=True),
                    item("number", "ocd_slots_per_day", _("lives per day"), min=1, max=24, width=60),
                ]),
                item("checks", "ocd_open_days", _("Days of opening of the studio"),
                     _("A closed day has no slot."), fields=[item("check", key, label) for key, label in days]),
                item("group", "ocd_hold", _("Slot held during the payment"),
                     _("Without payment, it is released and offered to the waiting list."), fields=[
                         item("number", "ocd_hold_minutes", _("minutes for an online payment"), min=5, max=1440, width=70),
                         item("number", "ocd_manual_hold_hours", _("hours for a payment checked by the team"), min=1, max=168, width=70),
                     ]),
                item("group", "ocd_limits", _("Book and move a live"),
                     _("The vendors do it themselves on the website, until these times."), fields=[
                         item("number", "ocd_min_notice_hours", _("hours before the live: last moment to book"), min=0, max=168, width=70),
                         item("number", "ocd_move_limit_hours", _("hours before: last moment to move"), min=0, max=720, width=70),
                     ]),
                item("check", "ocd_require_animatrice", _("Host required for the remote lives"),
                     _("A remote live without host creates an activity for the control room."),
                     warn_off=_("A remote live can then start without anyone of the team.")),
                item("select", "ocd_lives_channel_id", _("Tell the team at each booking"),
                     _("A message in this Discuss channel for each confirmed booking."),
                     options=self._ocd_record_options(
                         self.env["discuss.channel"].sudo().search([("channel_type", "=", "channel")]), _("Nobody")
                     )),
                item("select", "ocd_live_responsible_id", _("Manager of the lives"),
                     _("Receives the activities of the lives: host to choose, replay to publish."),
                     options=self._ocd_record_options(
                         self.env["res.users"].sudo().search([("share", "=", False)]), _("Nobody")
                     )),
                item("select", "ocd_calendar_mode", _("Calendars"),
                     _("One calendar when all the lives are broadcast by the same account."),
                     options=self._ocd_selection_options("ocd_calendar_mode")),
                item("select", "ocd_booking_flow", _("Order of the steps on the website"),
                     options=self._ocd_selection_options("ocd_booking_flow")),
                item("group", "ocd_studio_place", _("Place of the studio"),
                     _("The slots are set in the time of the studio."), fields=[
                         item("text", "ocd_studio_city", _("City"), width=140, before=True, required=True),
                         item("select", "ocd_studio_tz", _("Time zone"), before=True,
                              options=self._ocd_selection_options("ocd_studio_tz")),
                     ]),
                item("chips", "ocd_packages", _("The packages"),
                     _("What each package gives and its price are set on the package."),
                     chips=[
                         f"{package.name} · {format_amount(self.env, package.list_price, company.currency_id)}"
                         for package in packages
                     ],
                     link={"label": _("Packages and pass"), "action": "ocd_live.product_template_action_ocd_package"}),
                item("info", "ocd_price_rules", _("Price of the hours"),
                     _("Some hours cost more or less, e.g. Saturday evening +25 %. Without a rule, the price of the package."),
                     link={"label": _("Price of the hours"), "action": "ocd_live.ocd_live_price_rule_action"}),
            ],
        }

    @api.model
    def _ocd_section_directory(self):
        _ = self.env._
        company = self.env.company
        item = self._ocd_item
        return {
            "key": "directory",
            "sequence": 20,
            "icon": "AN",
            "label": _("Directory of the lives"),
            "title": _("Directory of the lives"),
            "items": [
                item("info", "ocd_windows", _("Checking windows of the links"), self._ocd_windows_text(),
                     link={"label": _("Checking windows"), "action": "ocd_live.ocd_directory_window_action"}),
                item("money", "ocd_pass_price", _("Price of the directory pass"),
                     _("Shows the lives of the vendor in the directory, for the days of the pass."),
                     get="_ocd_get_pass_price", set="_ocd_set_pass_price",
                     suffix=company.currency_id.symbol, width=110),
                item("number", "ocd_pass_reminder_days", _("Reminder before the end of the pass"),
                     _("On WhatsApp, with the link to renew it."), suffix=_("days before"), min=0, max=60, width=70),
                item("select", "ocd_vendor_login", _("How the vendors and the couriers log in"),
                     _("The personal link and the code go on WhatsApp. The couriers have no password: with « Number and password », they receive a code."),
                     options=self._ocd_selection_options("ocd_vendor_login")),
                item("info", "ocd_countries", self._ocd_countries_title(),
                     _("Offered in the forms of the website (WhatsApp number, directory): the vendors of these countries book and send their links, the couriers and the customers find their country. The directory shows the countries that have lives."),
                     link={"label": _("Countries"), "action": "ocd_live.ocd_country_action"}, span=2),
                item("info", "ocd_refuse_reasons", _("Reasons of refusal"),
                     _("Sent to the vendor when the team refuses a link."),
                     link={"label": _("Reasons of refusal"), "action": "ocd_live.ocd_listing_refuse_reason_action"}),
            ],
        }

    @api.model
    def _ocd_section_currencies(self):
        """The currency of each country: the prices written in the currency of the company,
        converted for the four zones (XOF, XAF, EUR, USD), the rates and an example."""
        _ = self.env._
        company = self.env.company
        item = self._ocd_item
        Currencies = self.env["ocd.live.currencies"]
        ready = Currencies._ocd_is_set_up()
        link = {"label": _("Pricelists"), "action": "product.product_pricelist_action2"}
        zones = item(
            "chips", "ocd_currency_zones", _("Currency of each country"),
            _("The prices are written in %(currency)s. Each country sees them, books and pays in its currency: "
              "XOF in the 8 countries of the UEMOA, XAF in the 6 countries of the CEMAC (CamPay takes this one), "
              "EUR in Europe and the rest of Africa, USD in the Americas, Asia and Oceania.",
              currency=company.currency_id.name),
            chips=Currencies._ocd_zone_chips() if ready else [],
            button={
                "label": _("Update the countries and the rates") if ready else _("Put the currencies by country in place"),
                "method": "_ocd_currencies_setup_button",
            },
            span=2,
        )
        if ready:
            zones["link"] = link
        items = [zones]
        if ready:
            items += [
                item("info", "ocd_currency_rates", _("Rates"), Currencies._ocd_rates_text(company),
                     button={"label": _("Read the dollar of the day"), "method": "_ocd_usd_rate_button"},
                     note=_("Every day by itself."), note_tone="green"),
                item("info", "ocd_currency_example", _("What a customer pays"), Currencies._ocd_example_text(),
                     note=_("Rounded to the unit in euros and in dollars."), note_tone="none"),
            ]
        else:
            items.append(item(
                "info", "ocd_currency_off", _("Today: one currency for every country"),
                _("Every price is shown and paid in %(currency)s, whatever the country: CamPay (XAF only) is not offered.",
                  currency=company.currency_id.name),
            ))
        return {
            "key": "currencies",
            "sequence": 45,
            "icon": "DV",
            "label": _("Currencies by country"),
            "title": _("Currencies by country"),
            "items": items,
        }

    def _ocd_currencies_setup_button(self):
        self.env["ocd.live.currencies"]._ocd_setup()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": self.env._("Currencies by country in place: each country sees its prices in its currency."),
            },
        }

    def _ocd_usd_rate_button(self):
        Currencies = self.env["ocd.live.currencies"]
        usd_per_euro = Currencies._ocd_read_usd_per_euro()
        if usd_per_euro:
            Currencies._ocd_set_rates(self.env.company, usd_per_euro)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success" if usd_per_euro else "warning",
                "message": self.env._("Dollar of the day: 1 € = %s $.", formatLang(self.env, usd_per_euro, digits=4))
                if usd_per_euro
                else self.env._("The European Central Bank does not answer: the last rate is kept. Try again later."),
            },
        }

    # === HELPERS OF THE SECTIONS === #

    @api.model
    def _ocd_selection_options(self, fname):
        field = self.env.company._fields[fname]
        return [{"value": value, "label": label} for value, label in field._description_selection(self.env)]

    @api.model
    def _ocd_record_options(self, records, empty_label=None):
        options = [{"value": False, "label": empty_label}] if empty_label else []
        return options + [{"value": record.id, "label": record.display_name} for record in records]

    @api.model
    def _ocd_hours_text(self):
        company = self.env.company
        start = company.ocd_first_slot_hour or 0.0
        end = start + (company.ocd_slot_hours or 0.0) * (company.ocd_slots_per_day or 0)
        return self.env._(
            "%(count)s lives of %(duration)s per day, from %(start)s to %(end)s.",
            count=company.ocd_slots_per_day,
            duration=self._ocd_hour_label(company.ocd_slot_hours or 0.0, duration=True),
            start=self._ocd_hour_label(start),
            end=self._ocd_hour_label(end % 24),
        )

    @api.model
    def _ocd_hour_label(self, value, duration=False):
        hours, minutes = int(value), round((value - int(value)) * 60)
        if minutes == 60:
            hours, minutes = hours + 1, 0
        if duration:
            return f"{hours} h {minutes:02d}" if minutes else f"{hours} h"
        return f"{hours:02d}:{minutes:02d}"

    @api.model
    def _ocd_windows_text(self):
        windows = self.env["ocd.directory.window"].sudo().search(
            [("company_id", "in", (self.env.company.id, False))], order="start_hour"
        )
        if not windows:
            return self.env._("No window: the links cannot be sent.")
        hours = self.env._(" and ").join(
            f"{self._ocd_hour_label(window.start_hour)} – {self._ocd_hour_label(window.end_hour)}" for window in windows
        )
        return self.env._(
            "%s. A link sent out of a window waits for the next one; the vendor is told.", hours
        )

    @api.model
    def _ocd_country_records(self):
        """The countries offered by OCD Live, in their order on the website."""
        Country = self.env["res.country"].sudo()
        return Country.browse([country.id for country, _group in Country._ocd_ordered()])

    @api.model
    def _ocd_country_names(self):
        return self._ocd_country_records().mapped("name")

    @api.model
    def _ocd_countries_title(self):
        """ "Open countries: 112 (54 in Africa, 23 in Europe…)" """
        countries = self._ocd_country_records()
        labels = dict(countries._fields["ocd_continent"]._description_selection(self.env))
        parts = [
            self.env._("%(count)s in %(continent)s", count=count, continent=labels[continent])
            for continent in ("africa", "europe", "americas", "asia", "oceania")
            if (count := len(countries.filtered(lambda c, continent=continent: c.ocd_continent == continent)))
        ]
        return self.env._("Open countries: %(count)s (%(parts)s)", count=len(countries), parts=", ".join(parts))

    @api.model
    def _ocd_product_price(self, xmlid):
        product = self.env.ref(xmlid, raise_if_not_found=False)
        return product.sudo().list_price if product else 0.0

    @api.model
    def _ocd_set_product_price(self, xmlid, price):
        product = self.env.ref(xmlid, raise_if_not_found=False)
        if not product:
            raise UserError(self.env._("This package does not exist any more."))
        product.sudo().list_price = price

    def _ocd_get_discovery_price(self):
        return self._ocd_product_price("ocd_live.product_package_discovery")

    def _ocd_set_discovery_price(self, price):
        self._ocd_set_product_price("ocd_live.product_package_discovery", price)

    def _ocd_get_pass_price(self):
        return self._ocd_product_price("ocd_live.product_directory_pass")

    def _ocd_set_pass_price(self, price):
        self._ocd_set_product_price("ocd_live.product_directory_pass", price)

    # === VALUES === #

    @api.model
    def _ocd_all_items(self, sections=None):
        for section in sections if sections is not None else self._ocd_sections():
            for item in section["items"]:
                yield item
                yield from item.get("fields", [])

    @api.model
    def _ocd_value_items(self, sections=None):
        return [item for item in self._ocd_all_items(sections) if item["kind"] in VALUE_KINDS]

    @api.model
    def _ocd_read_values(self, sections):
        company = self.env.company.sudo()
        values = {}
        for item in self._ocd_value_items(sections):
            if item.get("get"):
                values[item["key"]] = getattr(self.sudo(), item["get"])(*item.get("args", []))
                continue
            fname = item.get("field", item["key"])
            value = company[fname]
            field = company._fields[fname]
            if field.type == "many2one":
                value = value.id or False
            elif field.type == "date":
                value = fields.Date.to_string(value) if value else False
            elif field.type in ("char", "text", "selection"):
                value = value or ""
            values[item["key"]] = value
        return values

    @api.model
    def _ocd_check_values(self, values):
        """Checks between settings, on all the values after the change: {key: message}.
        Extended by the other modules."""
        errors = {}
        end = values["ocd_first_slot_hour"] + values["ocd_slot_hours"] * values["ocd_slots_per_day"]
        if end > 24:
            errors["ocd_slots_per_day"] = self.env._("The last live would end after midnight.")
        if not any(values[fname] for fname in OPEN_DAY_FIELDS):
            errors["ocd_open_mon"] = self.env._("Open the studio at least one day.")
        return errors

    @api.model
    def _ocd_parse(self, item, raw):
        """The value of `item` from the page, checked; raise UserError with the message to
        show next to the setting."""
        _ = self.env._
        kind = item["kind"]
        field = self.env.company._fields.get(item.get("field", item["key"])) if not item.get("set") else None
        if kind == "check":
            return bool(raw)
        if kind in ("number", "money", "time"):
            try:
                number = float(raw)
            except (TypeError, ValueError):
                raise UserError(_("Type a number.")) from None
            if field is not None and field.type == "integer" or item.get("integer"):
                if number != int(number):
                    raise UserError(_("Type a whole number."))
                number = int(number)
            low, high = item.get("min", 0), item.get("max")
            if number < low:
                raise UserError(_("At least %s.", low))
            if high is not None and number > high:
                raise UserError(_("At most %s.", high))
            return number
        if kind == "date":
            if not raw:
                if item.get("required"):
                    raise UserError(_("Choose a date."))
                return False
            try:
                return fields.Date.to_date(raw)
            except (TypeError, ValueError):
                raise UserError(_("Choose a date.")) from None
        if kind == "select":
            for option in item.get("options", []):
                if str(option["value"]) == str(raw) or (not option["value"] and not raw):
                    return option["value"]
            raise UserError(_("Choose one of the list."))
        if kind == "text":
            text = (raw or "").strip()
            if item.get("required") and not text:
                raise UserError(_("Fill in this setting."))
            if len(text) > item.get("size", 80):
                raise UserError(_("Too long."))
            return text
        raise UserError(_("This setting cannot be changed here."))
