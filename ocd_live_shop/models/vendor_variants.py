"""Sizes and colours from the creation (chantier 21, 3.5 of the plan of « My products », design
TaillesCouleurs).

The team chooses the attributes offered to the vendors (Size, Color, Shoe size…: « Offered To The
Vendors » on the attribute) and their values. Adding a product, the vendor ticks the sizes and the
colours it exists in and gives the stock of each: the product gets its variants of Odoo at once,
the same price for all, and is checked by the team as before; the photo of each colour comes
after (chantier 19). On a product on sale, the vendor adds a size or a colour of an attribute it
already has (stock 0): a value is never removed, at 0 piece it shows « Sold out »."""
from itertools import product as cartesian

from odoo import api, fields, models
from odoo.exceptions import UserError

# The most choices (a size and a colour each) a product of a vendor gets from their space
MAX_COMBINATIONS = 100

# Offered at the installation when the attributes of Odoo have no value yet: (English, French,
# colour of the swatch)
DEFAULT_SIZES = ("XS", "S", "M", "L", "XL", "XXL", "3XL")
DEFAULT_COLOURS = (
    ("Black", "Noir", "#15130F"), ("White", "Blanc", "#FFFFFF"), ("Red", "Rouge", "#C8102E"),
    ("Blue", "Bleu", "#1F4FA3"), ("Green", "Vert", "#2E8B57"), ("Yellow", "Jaune", "#F2C200"),
    ("Pink", "Rose", "#F4A6C0"), ("Orange", "Orange", "#F46A00"), ("Purple", "Violet", "#6A3D9A"),
    ("Brown", "Marron", "#7B4A2D"), ("Grey", "Gris", "#8A9097"), ("Beige", "Beige", "#E8D9B5"),
    ("Gold", "Doré", "#C9A227"),
)


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    ocd_for_vendors = fields.Boolean(
        string="Offered To The Vendors",
        help="The vendors choose its values when they add a product (sizes, colours…).",
    )

    @api.model
    def _ocd_vendor_attributes(self):
        """The attributes offered to the vendors, with values, in their order."""
        return self.sudo().search([("ocd_for_vendors", "=", True), ("create_variant", "=", "always")]).filtered(
            "value_ids"
        )

    @api.model
    def _ocd_init_vendor_attributes(self):
        """At the installation: the sizes and the colours of Odoo offered to the vendors, with
        common values when they have none (never twice the same value). Nothing changes once the
        team chose its attributes."""
        Attribute = self.sudo()
        if Attribute.search_count([("ocd_for_vendors", "=", True)], limit=1):
            return
        french = self.env["res.lang"]._ocd_is_active("fr_FR")
        size = self.env.ref("product.pa_size", raise_if_not_found=False)
        colour = self.env.ref("product.pa_color", raise_if_not_found=False)
        for attribute, values in ((size, [(name, name, False) for name in DEFAULT_SIZES]), (colour, DEFAULT_COLOURS)):
            if not attribute:
                continue
            attribute = attribute.sudo()
            if not attribute.value_ids:
                for english, french_name, swatch in values:
                    value = self.env["product.attribute.value"].sudo().with_context(lang="en_US").create({
                        "attribute_id": attribute.id, "name": english, "html_color": swatch or False,
                    })
                    if french and french_name != english:
                        value.with_context(lang="fr_FR").name = french_name
            attribute.write({"ocd_for_vendors": True, "create_variant": "always"})


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _ocd_read_chosen_values(self, value_ids):
        """{attribute: values} of the values ticked by the vendor, only of the attributes offered
        to them, in the order of the attributes."""
        values = self.env["product.attribute.value"].sudo().browse(value_ids).exists()
        offered = self.env["product.attribute"]._ocd_vendor_attributes()
        chosen = {}
        for attribute in offered:
            picked = values.filtered(lambda value, attribute=attribute: value.attribute_id == attribute)
            if picked:
                chosen[attribute] = picked.sorted(lambda value: (value.sequence, value.id))
        return chosen

    @api.model
    def _ocd_combinations(self, chosen):
        """Each choice (a value of each attribute) of `chosen`, as a tuple of values, and its key
        in the form (« 12-40 »: the ids of the values, sorted)."""
        lists = [list(values) for values in chosen.values()]
        combos = [tuple(combo) for combo in cartesian(*lists)] if lists else []
        if len(combos) > MAX_COMBINATIONS:
            raise UserError(self.env._("%s choices at most: tick fewer sizes or colours.", MAX_COMBINATIONS))
        return [(combo, "-".join(str(value_id) for value_id in sorted(value.id for value in combo))) for combo in combos]

    def _ocd_vendor_set_variants(self, chosen, quantities):
        """Give the new product of a vendor its sizes and colours (`chosen`, {attribute: values}),
        then the stock of each choice (`quantities`, {key of the choice: pieces})."""
        self.ensure_one()
        product = self.sudo()
        product.write({"attribute_line_ids": [
            fields.Command.create({"attribute_id": attribute.id, "value_ids": [fields.Command.set(values.ids)]})
            for attribute, values in chosen.items()
        ]})
        for variant in product.product_variant_ids:
            key = "-".join(str(value_id) for value_id in sorted(
                variant.product_template_attribute_value_ids.product_attribute_value_id.ids
            ))
            pieces = int(quantities.get(key) or 0)
            if pieces > 0:
                variant._ocd_change_stock(pieces)
        return product.product_variant_ids

    def _ocd_vendor_addable_values(self):
        """{attribute: values} the vendor may add to this product: the values not on it yet of
        the attributes offered to the vendors that the product already has."""
        self.ensure_one()
        offered = self.env["product.attribute"]._ocd_vendor_attributes()
        addable = {}
        for line in self.sudo().attribute_line_ids:
            if line.attribute_id in offered:
                missing = line.attribute_id.value_ids - line.value_ids
                if missing:
                    addable[line.attribute_id] = missing.sorted(lambda value: (value.sequence, value.id))
        return addable

    def _ocd_vendor_add_values(self, values):
        """Add sizes or colours to a product of a vendor: new choices without stock (to fill in
        « My stock »). Return the values added."""
        self.ensure_one()
        product = self.sudo()
        allowed = self.env["product.attribute.value"].browse()
        for missing in product._ocd_vendor_addable_values().values():
            allowed |= missing
        values = values & allowed
        if not values:
            raise UserError(self.env._("Choose a size or a colour to add."))
        lines = product.attribute_line_ids
        combos = 1
        for line in lines:
            combos *= len(line.value_ids | values.filtered(lambda value, line=line: value.attribute_id == line.attribute_id))
        if combos > MAX_COMBINATIONS:
            raise UserError(self.env._("%s choices at most: tick fewer sizes or colours.", MAX_COMBINATIONS))
        product.write({"attribute_line_ids": [
            fields.Command.update(line.id, {"value_ids": [fields.Command.link(value.id) for value in values
                                                          if value.attribute_id == line.attribute_id]})
            for line in lines if values.filtered(lambda value, line=line: value.attribute_id == line.attribute_id)
        ]})
        product.message_post(body=self.env._("Added by the vendor: %s", ", ".join(values.mapped("name"))))
        return values
