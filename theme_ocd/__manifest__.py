{
    "name": "OCD Live",
    "summary": "Live shopping, fonts, colours, buttons, header and footer of OCD Live for the whole site",
    "description": """
Theme of the site of OCD Live
=============================

The pages of OCD Live (booking, lives of the moment, shop, vendor space) have their own frame.
This theme gives the other pages of the site (recruitment, contact, login, portal of the
customers, pages made with the website builder) the look of the validated design:

- fonts Bricolage Grotesque (titles) and Figtree (texts);
- colours of OCD Live: orange, ink, sand; palette "OCD Live" in the website builder;
- round buttons, fields with large corners, white header with the logo, dark footer.

Choose it in Website > Configuration > Settings > Choose a theme (or in the website builder,
Theme > Change theme).
""",
    "category": "Theme",
    "sequence": 10,
    "version": "20.0.1.0.0",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["website"],
    "data": [
        "data/generate_primary_template.xml",
    ],
    "images": [
        "static/description/cover.png",
        "static/description/theme_ocd_screenshot.jpg",
    ],
    "assets": {
        "web._assets_primary_variables": [
            "theme_ocd/static/src/scss/primary_variables.scss",
        ],
        "web._assets_frontend_helpers": [
            ("prepend", "theme_ocd/static/src/scss/bootstrap_overridden.scss"),
        ],
        "web.assets_frontend": [
            "theme_ocd/static/src/scss/theme.scss",
        ],
    },
    "installable": True,
}
