{
    "name": "Cameroon: Cities, Districts and Delivery Zones",
    "summary": "Regions, cities and districts of Cameroon, delivery landmarks and "
    "delivery methods restricted by city or district",
    "description": """
Cameroon addresses and delivery zones
=====================================

- The 10 regions of Cameroon, its main cities and the districts (quartiers) of
  Douala and Yaoundé, all editable and importable from the backend.
- Checkout and portal address forms: city chosen from a list, district list
  loaded from the selected city, and a mandatory delivery landmark
  ("point de repère"); the street becomes optional for Cameroon.
- Delivery methods can be restricted to cities or districts, and can exclude
  cities or countries (e.g. "other cities of Cameroon", "international").
- Ready-made delivery methods to configure: home delivery in Douala, shipping
  to other cities of Cameroon and international shipping.
""",
    "version": "20.0.1.0.2",
    "category": "Website/Website",
    "author": "RollBackk",
    "license": "OPL-1",
    "depends": ["website_sale", "base_address_extended"],
    "data": [
        "security/ir.access.csv",
        "data/res_country_data.xml",
        "data/res.country.state.csv",
        "data/res.city.csv",
        "data/res.city.district.csv",
        "data/delivery_carrier_data.xml",
        "views/res_city_district_views.xml",
        "views/res_city_views.xml",
        "views/res_partner_views.xml",
        "views/delivery_carrier_views.xml",
        "views/address_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "delivery_cameroon/static/src/interactions/address.js",
        ],
    },
    "installable": True,
}
