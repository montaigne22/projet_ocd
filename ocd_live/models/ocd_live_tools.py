from odoo import api, models, release

AREAS = ("lives", "directory", "shop", "deliveries", "money")
ALL = list(AREAS)


class OcdLiveTools(models.AbstractModel):
    """Tools of Odoo used by OCD Live, as in the validated design (BoOutils): the standard
    applications, the modules of the repository and the modules of OCD Live, each with what it
    is used for and whether it is installed here."""

    _name = "ocd.live.tools"
    _description = "OCD Live Tools"

    @api.model
    def _ocd_apps(self):
        _ = self.env._
        return [
            ("website", _("Website"), _("Pages, directory, boutiques of the vendors"), ["lives", "directory", "shop"]),
            ("website_sale", _("eCommerce"), _("Shop of OCD: products, cart, order"), ["shop"]),
            ("sale_management", _("Sales"), _("Orders of the shop and live packages"), ["shop", "lives"]),
            ("stock", _("Inventory"), _("A parcel per vendor, consignment, returns"), ["deliveries"]),
            ("account", _("Invoicing"), _("Bills of the vendors, credit notes, cash of the couriers"), ["money"]),
            ("contacts", _("Contacts"), _("Customers and vendors, with a landmark"), ALL),
            ("hr", _("Employees"), _("Control room, hosts, OCD couriers"), ["lives", "deliveries"]),
            ("hr_recruitment", _("Recruitment"), _("Job of live host on the website"), ["lives"]),
            ("mail", _("Discuss"), _("Channels of the lives, the deliveries and the cash"), ALL),
            ("calendar", _("Calendar"), _("Meetings of the team"), ["lives"]),
            ("base_automation", _("Automations"), _("Rules changed without code"), ALL),
            ("portal", _("Portal"), _("Space of the vendors, delivery app"), ["shop", "deliveries"]),
        ]

    @api.model
    def _ocd_repository(self):
        _ = self.env._
        return [
            ("whatsapp_cloud", _("Conversations in Odoo, templates sent to Meta, STOP and START."), ALL, ""),
            ("whatsapp_cloud_sale", _("Messages of the orders, tracking, rating after the delivery."), ["shop", "deliveries"], ""),
            ("payment_campay", _("MTN MoMo, Orange Money, card. Checks the pending payments again."),
             ["lives", "directory", "shop", "money"], _("Cameroon and Central African CFA francs only.")),
            ("delivery_cameroon", _("Cities, districts, landmark, prices per district."), ["shop", "deliveries"],
             _("Cameroon only: ocd_delivery_togo adds Togo.")),
        ]

    @api.model
    def _ocd_not_needed(self):
        _ = self.env._
        return [
            (_("Planning"), _("Calendar of the studio in ocd_live"), ["lives"]),
            (_("Appointments"), _("Booking on the website by ocd_live"), ["lives"]),
            (_("Subscriptions"), _("Directory pass: product, end date, reminder"), ["directory"]),
            (_("Field Service"), _("Delivery app on the portal"), ["deliveries"]),
            (_("Accounting"), _("Invoicing is enough for OCD"), ["money"]),
            (_("Studio"), _("Modules written, tested and versioned"), ALL),
        ]

    @api.model
    def get_tools_data(self):
        Module = self.env["ir.module.module"].sudo()
        names = [row[0] for row in self._ocd_apps()] + [row[0] for row in self._ocd_repository()]
        ocd_modules = Module.search([("name", "=like", "ocd\\_%")], order="name")
        installed = set(Module.search([("name", "in", names + ocd_modules.mapped("name")), ("state", "=", "installed")]).mapped("name"))
        _ = self.env._
        return {
            "areas": [
                {"key": "all", "label": _("All")},
                {"key": "lives", "label": _("Lives")},
                {"key": "directory", "label": _("Directory")},
                {"key": "shop", "label": _("Shop")},
                {"key": "deliveries", "label": _("Deliveries")},
                {"key": "money", "label": _("Money")},
            ],
            "apps": [
                {"key": name, "name": label, "use": use, "tags": tags, "installed": name in installed}
                for name, label, use, tags in self._ocd_apps()
            ],
            "repository": [
                {"key": name, "name": name, "use": use, "tags": tags, "limit": limit, "installed": name in installed}
                for name, use, tags, limit in self._ocd_repository()
            ],
            "ocd": [
                {
                    "key": module.name,
                    "name": module.name,
                    "use": module.summary or module.shortdesc,
                    "tags": ALL,
                    "installed": module.name in installed,
                }
                for module in ocd_modules
            ],
            "not_needed": [
                {"key": f"ent_{index}", "name": name, "use": use, "tags": tags}
                for index, (name, use, tags) in enumerate(self._ocd_not_needed())
            ],
            "edition": _("Odoo %s Community", release.major_version),
        }
