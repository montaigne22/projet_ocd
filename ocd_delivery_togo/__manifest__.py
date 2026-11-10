{
    "name": "Togo: Cities, Districts and Delivery Zones",
    "summary": "Regions and cities of Togo, districts of Lome, delivery landmark in the "
    "address, delivery methods for Lome and the other cities of Togo",
    "description": """
Togo addresses and delivery zones
=================================

Extends delivery_cameroon to Togo, so that the shop delivers in Cameroon and
in Togo from the start:

- the 5 regions of Togo, its main cities and the districts (quartiers) of
  Lome, editable from the backend;
- the same address form as in Cameroon: city from a list, district of the
  city, mandatory landmark, optional street;
- delivery methods for Lome and for the other cities of Togo, to price and
  publish (Website > Configuration > Delivery Methods).

The prices of the shop are in francs CFA: the franc of Central Africa (XAF,
Cameroon) and the franc of West Africa (XOF, Togo) have the same value.
""",
    "version": "20.0.1.0.0",
    "category": "Website/Website",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["delivery_cameroon"],
    "data": [
        "data/res_country_data.xml",
        "data/res.country.state.csv",
        "data/res.city.csv",
        "data/res.city.district.csv",
        "data/delivery_carrier_data.xml",
    ],
    "installable": True,
}
