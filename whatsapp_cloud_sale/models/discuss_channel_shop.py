import os

from odoo import fields, models
from odoo.tools import format_amount

from odoo.addons.whatsapp_cloud.const import MAX_LIST_ROWS, MAX_ROW_DESCRIPTION
from odoo.addons.whatsapp_cloud.tools import simplify

MAX_STORES = 5
MAX_ORDERS_TO_PAY = 3
MAX_DESCRIPTION = 160
# choices of a list, with the "Another..." one
MAX_CHOICES = MAX_LIST_ROWS - 1
CITY_REPLY_PREFIX = "whatsapp_city_"
OTHER_CITY_REPLY_ID = "whatsapp_city_other"
DISTRICT_REPLY_PREFIX = "whatsapp_district_"
ZONE_REPLY_PREFIX = "whatsapp_zone_"
OTHER_DISTRICT_REPLY_ID = "whatsapp_district_other"


def shorten(text, size):
    """The text cut to the size, with an ellipsis when cut."""
    return text if len(text) <= size else text[:size - 1].rstrip(", ") + "…"


def short_labels(names):
    """The names without the beginning they all share ("Delivery to Douala – Centre",
    "Delivery to Douala – Periphery": "Centre", "Periphery"), cut after a separator."""
    if len(names) < 2:
        return names
    prefix = os.path.commonprefix(names)
    cut = max([prefix.rfind(sep) + len(sep) for sep in (" – ", " - ", ": ", " ") if sep in prefix] or [0])
    labels = [name[cut:].strip() or name for name in names]
    return labels if len(set(labels)) == len(labels) else names


class DiscussChannel(models.Model):
    """Answers of the welcome menu about the shop: stores, payment, delivery fees."""

    _inherit = "discuss.channel"

    def _whatsapp_get_step_handlers(self):
        return {
            **super()._whatsapp_get_step_handlers(),
            "delivery_city": self._whatsapp_step_delivery_city,
            "delivery_district": self._whatsapp_step_delivery_district,
        }

    def _whatsapp_customer_env(self):
        """The conversation in the language of the customer, for the texts sent to them."""
        self.ensure_one()
        return self.with_context(lang=self._whatsapp_get_lang())

    # === STORES === #

    def _whatsapp_get_stores(self):
        """Stores of the company: the warehouses of the published "Pick up in store"
        delivery methods (Click & Collect), else its warehouses with an address."""
        self.ensure_one()
        company = self.whatsapp_account_id.company_id
        Carrier = self.env["delivery.carrier"].sudo()
        if "warehouse_ids" in Carrier._fields:
            stores = Carrier.search([
                ("delivery_type", "=", "in_store"),
                ("is_published", "=", True),
                ("company_id", "in", [False, company.id]),
            ]).warehouse_ids
            if stores:
                return stores
        return self.env["stock.warehouse"].sudo().search([
            ("company_id", "=", company.id),
        ]).filtered(lambda warehouse: warehouse.partner_id.street or warehouse.partner_id.city)

    def _whatsapp_send_stores(self):
        """The stores with their address, phone and opening hours, then their location to
        open them in the maps of the phone."""
        self.ensure_one()
        channel = self._whatsapp_customer_env()
        stores = channel._whatsapp_get_stores()[:MAX_STORES].with_context(channel.env.context)
        if not stores:
            channel._whatsapp_send_answer(channel.env._(
                "Our team will tell you where to find our products."
            ))
            return
        blocks = [channel.env._("Our stores:")]
        for store in stores:
            partner = store.partner_id
            lines = [f"*{partner.name or store.name}*", store._whatsapp_get_address()]
            if partner.phone:
                lines.append(f"📞 {partner.phone}")
            lines += [f"🕘 {line}" for line in store._whatsapp_get_opening_hours()]
            blocks.append("\n".join(filter(None, lines)))
        channel._whatsapp_send_bot_text("\n\n".join(blocks))
        for store in stores:
            partner = store.partner_id
            if partner.partner_latitude or partner.partner_longitude:
                channel._whatsapp_send_location(
                    partner.partner_latitude, partner.partner_longitude,
                    partner.name or store.name, store._whatsapp_get_address(),
                )
        channel._whatsapp_send_follow_up()

    # === PAYMENT === #

    def _whatsapp_get_orders_to_pay(self):
        """Orders and quotations of the customer that can be paid online now."""
        self.ensure_one()
        return self._whatsapp_get_orders(limit=20).filtered(
            lambda order: order._whatsapp_get_amount_to_pay() > 0
        )[:MAX_ORDERS_TO_PAY]

    def _whatsapp_send_orders_to_pay(self):
        """The payment links of the orders to pay (Mobile Money, card... the payment methods
        of the site)."""
        self.ensure_one()
        channel = self._whatsapp_customer_env()
        env = channel.env
        orders = channel._whatsapp_get_orders_to_pay().with_context(env.context)
        if not orders:
            channel._whatsapp_send_answer(env._("You have no order to pay."))
            return
        blocks = [env._("Pay online, it is secure:")]
        for order in orders:
            amount = order._whatsapp_get_amount_to_pay()
            blocks.append(env._(
                "%(order)s: %(amount)s to pay\n%(link)s",
                order=order.name,
                amount=format_amount(env, amount, order.currency_id),
                link=order._whatsapp_get_payment_link(amount),
            ))
        channel._whatsapp_send_answer("\n\n".join(blocks))

    # === DELIVERY FEES === #

    def _whatsapp_get_delivery_carriers(self):
        """Published delivery methods of the company."""
        self.ensure_one()
        company = self.whatsapp_account_id.company_id
        return self.env["delivery.carrier"].sudo().search([
            ("is_published", "=", True), ("company_id", "in", [False, company.id]),
        ])

    def _whatsapp_ask_delivery_city(self, with_choices=True):
        """Ask the city of the delivery: the cities with their own delivery methods as
        choices, and "Another city" (the delivery methods of the other cities); written by
        the customer when they are too many."""
        self.ensure_one()
        channel = self._whatsapp_customer_env()
        env = channel.env
        carriers = channel._whatsapp_get_delivery_carriers()
        cities = (
            # the cities with their own delivery methods, or delivery zones of districts
            (carriers.city_ids | carriers.district_ids.city_id).sorted("name")
            if "city_ids" in carriers._fields else []
        )
        if not cities:
            # no delivery method limited to cities: the same fees everywhere
            channel._whatsapp_send_delivery_fees()
        elif with_choices and len(cities) <= MAX_CHOICES:
            choices = [
                (f"{CITY_REPLY_PREFIX}{city.id}", city.with_context(env.context).name, None)
                for city in cities
            ]
            choices.append((OTHER_CITY_REPLY_ID, env._("Another city"), None))
            channel._whatsapp_ask(
                "delivery_city", env._("Where should we deliver? Choose your city."),
                choices=choices, list_button=env._("Choose the city"),
            )
        else:
            channel._whatsapp_ask(
                "delivery_city", env._("Where should we deliver? Write the name of your city.")
            )

    def _whatsapp_step_delivery_city(self, wa_message, content, data):
        reply_id = content.get("reply_id") or ""
        if reply_id == OTHER_CITY_REPLY_ID:
            self._whatsapp_send_delivery_fees(other_city=True)
            return True
        name = (wa_message.body or "").strip()
        city = self._whatsapp_find_city(reply_id, name)
        if not city and not simplify(name):
            self._whatsapp_ask_delivery_city()
            return True
        if city and self._whatsapp_get_delivery_zones(city):
            self._whatsapp_ask_delivery_district(city)
            return True
        self._whatsapp_send_delivery_fees(city=city, city_name=name)
        return True

    def _whatsapp_ask_delivery_district(self, city, with_choices=True):
        """Ask the district of the delivery: its districts as choices when they are few, else
        its delivery zones with their districts under their name; "Another district" to
        write it."""
        self.ensure_one()
        channel = self._whatsapp_customer_env()
        env = channel.env
        city_name = city.with_context(env.context).name
        data = {"city_id": city.id}
        if not with_choices:
            channel._whatsapp_ask(
                "delivery_district", env._("Write the name of your district in %s.", city_name),
                data=data,
            )
            return
        zones = channel._whatsapp_get_delivery_zones(city)
        districts = self.env["res.city.district"].union(zone[1] for zone in zones)
        if len(districts) <= MAX_CHOICES:
            text = env._("In which district of %s?", city_name)
            choices = [
                (f"{DISTRICT_REPLY_PREFIX}{district.id}", district.name, None)
                for district in districts.with_context(env.context).sorted("name")
            ]
        else:
            text = env._(
                "In which district of %s? Choose your zone: its districts are written under "
                "its name.", city_name,
            )
            choices = [
                (f"{ZONE_REPLY_PREFIX}{carrier.id}", label,
                 shorten(", ".join(zone_districts.with_context(env.context).mapped("name")),
                         MAX_ROW_DESCRIPTION))
                for carrier, zone_districts, label in zones[:MAX_CHOICES]
            ]
        choices.append((OTHER_DISTRICT_REPLY_ID, env._("Another district"), None))
        channel._whatsapp_ask(
            "delivery_district", text, data=data, choices=choices,
            list_button=env._("Choose the district"), force_list=len(districts) > MAX_CHOICES,
        )

    def _whatsapp_step_delivery_district(self, wa_message, content, data):
        reply_id = content.get("reply_id") or ""
        name = (wa_message.body or "").strip()
        city = self.env["res.city"].sudo().browse(data.get("city_id")).exists()
        if not city:
            self._whatsapp_ask_delivery_city()
            return True
        if reply_id == OTHER_DISTRICT_REPLY_ID:
            self._whatsapp_ask_delivery_district(city, with_choices=False)
            return True
        if reply_id.startswith(ZONE_REPLY_PREFIX):
            zone = self.env["delivery.carrier"].sudo().browse(
                int(reply_id.removeprefix(ZONE_REPLY_PREFIX) or 0)
            ).exists()
            self._whatsapp_send_delivery_fees(city=city, zone=zone)
            return True
        if reply_id.startswith(DISTRICT_REPLY_PREFIX):
            district = city.district_ids.filtered(
                lambda d: d.id == int(reply_id.removeprefix(DISTRICT_REPLY_PREFIX) or 0)
            )
        else:
            district = self._whatsapp_match_name(city.district_ids, name)
        if not district and not simplify(name):
            self._whatsapp_ask_delivery_district(city)
            return True
        self._whatsapp_send_delivery_fees(city=city, district=district, district_name=name)
        return True

    def _whatsapp_find_city(self, reply_id, name):
        """The city chosen in the list, or written by the customer (None when unknown)."""
        if "res.city" not in self.env:
            return None
        City = self.env["res.city"].sudo()
        if reply_id.startswith(CITY_REPLY_PREFIX):
            city = City.browse(int(reply_id.removeprefix(CITY_REPLY_PREFIX) or 0)).exists()
            if city:
                return city
        # the cities served first, then all the cities of their countries and of the company
        carriers = self._whatsapp_get_delivery_carriers()
        served = (carriers.city_ids | carriers.district_ids.city_id) if "city_ids" in carriers._fields else City
        city = self._whatsapp_match_name(served, name)
        if city:
            return city
        countries = served.country_id | self.whatsapp_account_id.company_id.country_id
        return self._whatsapp_match_name(
            City.search([("country_id", "in", countries.ids)] if countries else []), name
        )

    def _whatsapp_match_name(self, records, name):
        """The record named as the customer wrote it (without accents nor case), else the
        first one whose name starts with it; None when none matches."""
        text = simplify(name)
        if not text:
            return None
        names = {record: simplify(record.name) for record in records}
        exact = [record for record, simple in names.items() if simple == text]
        if exact:
            return exact[0]
        starting = [
            record for record, simple in names.items()
            if len(text) >= 3 and (simple.startswith(text) or text.startswith(simple))
        ]
        return starting[0] if starting else None

    def _whatsapp_get_delivery_zones(self, city):
        """Delivery zones of the city: its delivery methods limited to some of its districts,
        as [(delivery method, its districts in the city, short name)]."""
        self.ensure_one()
        carriers = self._whatsapp_get_delivery_carriers().filtered(
            lambda carrier: carrier.delivery_type != "in_store"
        )
        if "district_ids" not in carriers._fields or not city.district_ids:
            return []
        zones = [
            (carrier, carrier.district_ids & city.district_ids) for carrier in carriers
            if carrier.district_ids & city.district_ids
        ]
        labels = short_labels([carrier.name for carrier, _districts in zones])
        return [(carrier, districts, label) for (carrier, districts), label in zip(zones, labels)]

    def _whatsapp_send_delivery_fees(self, city=None, district=None, city_name="",
                                     district_name="", zone=None, other_city=False):
        """The delivery methods for the address (a city, a district, a delivery zone of the
        city, or the other cities), with their price, and the pickup in store."""
        self.ensure_one()
        channel = self._whatsapp_customer_env()
        env = channel.env
        Partner = env["res.partner"]
        company = channel.whatsapp_account_id.company_id
        vals = {
            "country_id": (city.country_id if city else company.country_id).id,
            "city": city.name if city else city_name,
        }
        if city and "city_id" in Partner._fields:
            vals["city_id"] = city.id
        if zone and city:
            district = (zone.district_ids & city.district_ids)[:1]
        if district:
            vals["district_id"] = district.id
        carriers = channel._whatsapp_get_delivery_carriers().with_context(env.context)
        currency = channel._whatsapp_get_shop_currency()
        pickups = carriers.filtered(lambda carrier: carrier.delivery_type == "in_store")
        deliveries = (carriers - pickups).filtered(
            lambda carrier: carrier._match_address(Partner.new(vals))
        )
        # district not found: the delivery zones of the city, "depending on the district"
        by_district = env["delivery.carrier"]
        if city and not district:
            by_district = env["delivery.carrier"].union(
                carrier for carrier, _districts, _label in channel._whatsapp_get_delivery_zones(city)
            ).with_context(env.context) - deliveries
        city_label = city.with_context(env.context).name if city else city_name
        if zone:
            labels = {
                carrier: label for carrier, _districts, label in channel._whatsapp_get_delivery_zones(city)
            }
            place = f"{city_label} ({labels[zone]})" if zone in labels else city_label
        else:
            place = ", ".join(filter(None, [
                district.with_context(env.context).name if district else district_name, city_label,
            ]))
        blocks = []
        if other_city:
            title = env._("Delivery to the other cities:")
        elif city and district_name and not district:
            title = env._(
                "%(district)s is not in our delivery zones of %(city)s: our fees depend on the "
                "district.", district=district_name, city=city_label,
            )
        elif place:
            title = env._("Delivery to %s:", place)
        else:
            title = env._("Our delivery methods:")
        lines = [channel._whatsapp_format_carrier(carrier, currency) for carrier in deliveries | by_district]
        if lines:
            blocks.append("\n".join([title, *lines]))
        else:
            blocks.append(
                env._("We do not deliver to the other cities yet.") if other_city
                else env._("We do not deliver to %s yet.", place)
            )
        if pickups:
            blocks.append("\n".join(
                [env._("Or pick up your order in store:")]
                + [channel._whatsapp_format_carrier(carrier, currency) for carrier in pickups]
            ))
        blocks.append(env._("The exact fees are shown when you order."))
        channel._whatsapp_send_answer("\n\n".join(blocks))

    def _whatsapp_get_shop_currency(self):
        """Currency of the prices for the customer: the one of their pricelist (the shop),
        else the one of the company."""
        self.ensure_one()
        company = self.whatsapp_account_id.company_id
        partner = self.whatsapp_partner_id.with_company(company)
        pricelist = partner.property_product_pricelist if partner else False
        return (pricelist and pricelist.currency_id) or company.currency_id

    def _whatsapp_format_carrier(self, carrier, currency):
        """A delivery method with its price in the currency, in the language of the
        conversation context."""
        env = self.env
        company = carrier.company_id or self.whatsapp_account_id.company_id
        today = fields.Date.context_today(self)

        def convert(amount):
            return company.currency_id._convert(amount, currency, company, today)

        price, minimum = carrier._whatsapp_get_price()
        if price is not None:
            price = convert(price)
        if price is None:
            fee = env._("price given when you order")
        elif not price:
            fee = env._("free")
        elif minimum:
            fee = env._("from %s", format_amount(env, price, currency))
        else:
            fee = format_amount(env, price, currency)
        if carrier.free_over and carrier.amount and price and carrier.delivery_type != "base_on_rule":
            fee = env._(
                "%(fee)s, free from %(amount)s",
                fee=fee, amount=format_amount(env, convert(carrier.amount), currency),
            )
        line = env._("• *%(name)s*: %(fee)s", name=carrier.name, fee=fee)
        description = (carrier.carrier_description or "").strip().split("\n")[0]
        if description:
            line += f"\n  {description[:MAX_DESCRIPTION]}"
        return line
