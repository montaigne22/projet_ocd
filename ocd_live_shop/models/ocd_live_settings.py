from odoo import api, models


class OcdLiveSettings(models.AbstractModel):
    """The shop on the settings page of OCD Live: shop and deliveries, payments and payouts."""

    _inherit = "ocd.live.settings"

    @api.model
    def _ocd_sections(self):
        return [*super()._ocd_sections(), self._ocd_section_shop(), self._ocd_section_payments()]

    @api.model
    def _ocd_section_shop(self):
        _ = self.env._
        company = self.env.company
        item = self._ocd_item
        symbol = company.currency_id.symbol
        return {
            "key": "shop",
            "sequence": 30,
            "icon": "SH",
            "label": _("Shop and deliveries"),
            "title": _("Shop and deliveries"),
            "items": [
                item("number", "ocd_default_commission", _("Default commission of OCD"),
                     _("Changed on the form of each vendor."), suffix="%", min=0, max=100, width=70),
                item("select", "ocd_default_delivery_mode", _("Who delivers, by default"),
                     _("For a new vendor sold by OCD. Changed on the form of the vendor."),
                     options=self._ocd_selection_options("ocd_default_delivery_mode")),
                item("number", "ocd_prep_hours", _("Time to prepare a parcel"),
                     _("Past this time, the vendor is reminded on WhatsApp."),
                     suffix=_("hours"), min=1, max=72, width=70),
                item("number", "ocd_escalation_hours", _("Alert to the dispatch"),
                     _("When the parcel is still not ready after the reminder: an OCD courier can take it over."),
                     suffix=_("hours after the reminder"), min=1, max=72, width=70),
                item("number", "ocd_code_max_attempts", _("Wrong codes before locking the parcel"),
                     _("A parcel is delivered only with the code of the customer."),
                     suffix=_("tries"), min=1, max=10, width=70),
                item("number", "ocd_max_failed_attempts", _("Failed attempts before the return"),
                     _("After the last one: back to the vendor, and a credit note when the customer paid online."),
                     suffix=_("attempts"), min=1, max=10, width=70),
                item("time", "ocd_cash_deadline", _("Cash handed over by the couriers"),
                     _("After this hour, the manager is alerted."), suffix=_("every evening")),
                item("number", "ocd_return_days", _("Return asked by the customer"),
                     _("From the tracking page. 0: no return from the website."),
                     suffix=_("days after the delivery"), min=0, max=365, width=70),
                item("group", "ocd_vendor_rates", _("Delivery prices of the vendors"),
                     _("The vendors who deliver set their prices between these amounts. 0: no limit."), fields=[
                         item("money", "ocd_vendor_rate_min", _("from"), before=True, suffix=symbol, width=100),
                         item("money", "ocd_vendor_rate_max", _("to"), before=True, suffix=symbol, width=100),
                     ]),
                item("number", "ocd_delivery_commission", _("Share of OCD on the deliveries of the vendors"),
                     _("Kept by OCD Live when the vendor delivers. The deliveries of the OCD couriers and of the agencies are kept by OCD Live."),
                     suffix="%", min=0, max=100, width=70),
                item("select", "ocd_stock_city_id", _("City of the OCD stock"),
                     _("The parcels of the OCD stock leave from this city, at the rates of OCD Live."),
                     options=self._ocd_record_options(self._ocd_stock_cities(), _("None"))),
                item("select", "ocd_deliveries_channel_id", _("Team channel of the deliveries"),
                     _("Late parcels, problems and cash are announced in this Discuss channel."),
                     options=self._ocd_record_options(
                         self.env["discuss.channel"].sudo().search([("channel_type", "=", "channel")]), _("Nobody")
                     )),
                item("info", "ocd_rates", _("Delivery rates"), self._ocd_rates_text(),
                     link={"label": _("Delivery rates"), "action": "ocd_live_shop.ocd_delivery_rate_action"},
                     button={"label": _("Create the rates from the delivery methods"), "method": "_ocd_rates_from_carriers_button"},
                     span=2),
            ],
        }

    @api.model
    def _ocd_section_payments(self):
        _ = self.env._
        company = self.env.company
        item = self._ocd_item
        providers = self._ocd_payment_providers()
        items = [
            item("check", f"ocd_provider_{provider.id}", provider.name, self._ocd_provider_text(provider),
                 get="_ocd_get_provider_published", set="_ocd_set_provider_published", args=[provider.id])
            for provider in providers
        ]
        items += [
            item("checks", "ocd_cod_methods", _("Paid at the door"),
                 _("How the customer pays when the parcel arrives."), fields=[
                     item("check", "ocd_cod_cash", _("cash")),
                     item("check", "ocd_cod_online", _("on the phone of the customer")),
                     item("check", "ocd_cod_momo_declared", _("Mobile Money declared by the courier")),
                 ]),
            item("select", "ocd_default_payout_frequency", _("Rhythm of the payouts"),
                 _("By default; changed on the form of each vendor."),
                 options=self._ocd_selection_options("ocd_default_payout_frequency")),
            item("select", "ocd_payout_weekday", _("Day of the payouts"),
                 _("The payouts are prepared the evening before; the team checks them."),
                 options=self._ocd_selection_options("ocd_payout_weekday")),
            item("money", "ocd_payout_min_amount", _("Minimum payout"),
                 _("Below, the amount waits for the next payout."),
                 suffix=company.currency_id.symbol, width=100),
            item("select", "ocd_payout_journal_id", _("Journal of the payouts"),
                 _("The payments to the vendors are recorded in it."),
                 options=self._ocd_record_options(
                     self.env["account.journal"].sudo().search(
                         [("company_id", "=", company.id), ("type", "in", ("bank", "cash"))]
                     ),
                     _("The first bank journal"),
                 )),
            item("info", "ocd_payout_proof", _("Paid out: only the parcels confirmed by code"),
                 _("A return accepted after a payout is withheld from the next one."),
                 note=_("Always: it protects the money of OCD Live."), note_tone="green"),
        ]
        missing = self._ocd_countries_without_online_payment(providers)
        if missing:
            shown = ", ".join(missing[:6])
            if len(missing) > 6:
                shown = _("%(countries)s and %(count)s others", countries=shown, count=len(missing) - 6)
            items.append(item(
                "warn", "ocd_payment_countries",
                _("No online payment in: %s", shown),
                _("The vendors and the customers of these countries pay with the payments checked by the team (Mobile Money, cash at the studio) or at the door. The card payment (Stripe) takes the payments of every country once its keys are entered."),
                link={"label": _("Payment providers"), "action": "payment.action_payment_provider"},
            ))
        return {
            "key": "payments",
            "sequence": 40,
            "icon": "PA",
            "label": _("Payments and payouts"),
            "title": _("Payments and payouts"),
            "items": items,
        }

    # === HELPERS === #

    @api.model
    def _ocd_stock_cities(self):
        company = self.env.company
        rates = self.env["ocd.delivery.rate"].sudo()._ocd_rates(company)
        countries = company.country_id | rates.origin_country_id | rates.country_id
        cities = self.env["res.city"].sudo().search([("country_id", "in", countries.ids)], order="name")
        return cities | company.ocd_stock_city_id

    @api.model
    def _ocd_rates_text(self):
        Rate = self.env["ocd.delivery.rate"].sudo().with_context(active_test=False)
        domain = [("company_id", "in", (self.env.company.id, False))]
        active = Rate.search_count(domain + [("active", "=", True)])
        archived = Rate.search_count(domain + [("active", "=", False)])
        if not active:
            return self.env._("No rate in use: the shop refuses every address. Add the rates of the OCD couriers and of the agencies.")
        return self.env._(
            "%(active)s rates in use, %(archived)s archived. Without a rate for an address, the shop refuses it before the payment.",
            active=active,
            archived=archived,
        )

    def _ocd_rates_from_carriers_button(self):
        created = self.env["ocd.delivery.rate"].sudo()._ocd_rates_from_carriers(self.env.company)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success" if created else "info",
                "message": self.env._("%s rates created: check their prices, then activate them.", len(created))
                if created else self.env._("No new delivery method to turn into rates."),
            },
        }

    @api.model
    def _ocd_payment_providers(self):
        return self.env["payment.provider"].sudo().search([
            ("company_id", "=", self.env.company.id),
            ("code", "!=", "none"),
            ("module_state", "in", ("installed", False)),
            ("active", "=", True),
        ], order="sequence, id")

    @api.model
    def _ocd_provider_text(self, provider):
        countries = provider.available_country_ids
        currencies = provider.available_currency_ids
        where = ", ".join(countries.mapped("name")) if countries else self.env._("every country")
        text = self.env._("Offered on the website for: %s.", where)
        if currencies:
            text = self.env._("%(text)s In %(currencies)s.", text=text, currencies=", ".join(currencies.mapped("name")))
        if provider.custom_mode == "cash_on_delivery":
            text = self.env._("Paid at the door: offered when every parcel of the order accepts it.")
        return text

    def _ocd_get_provider_published(self, provider_id):
        return bool(self.env["payment.provider"].sudo().browse(provider_id).exists().is_published)

    def _ocd_set_provider_published(self, provider_id, value):
        provider = self.env["payment.provider"].sudo().browse(provider_id).exists()
        if provider:
            provider.is_published = value

    @api.model
    def _ocd_countries_without_online_payment(self, providers):
        """The countries of OCD Live where no published provider takes the payments online
        (the payment at the door does not count)."""
        online = providers.filtered(lambda p: p.is_published and p.custom_mode != "cash_on_delivery")
        if any(not provider.available_country_ids for provider in online):
            return []
        covered = online.available_country_ids
        return [name for name in self._ocd_country_records().filtered(lambda c: c not in covered).mapped("name")]

    @api.model
    def _ocd_check_values(self, values):
        errors = super()._ocd_check_values(values)
        low, high = values.get("ocd_vendor_rate_min") or 0, values.get("ocd_vendor_rate_max") or 0
        if low and high and low > high:
            errors["ocd_vendor_rate_max"] = self.env._("At least the lowest price.")
        return errors
