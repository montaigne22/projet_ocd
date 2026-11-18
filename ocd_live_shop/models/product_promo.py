"""The promo price of a product (plan, 3.1; chantier 7, design ProgrammeSoirees): a price lower than
the price of the last days, until a date. It is applied where Odoo computes every price of a
product from its sales price (`_price_compute`): the shop, the product page, the cart, the orders,
the pricelists of each country (euros, dollars). The price struck through is the lowest price of
the product in the last days: a price raised just before does not make a promo."""
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_amount

from odoo.addons.ocd_live import tools

# An order started during a promo keeps its promo price this long after the end of the promo,
# while it is paid (the time a customer takes to pay with Mobile Money)
PROMO_GRACE = timedelta(hours=2)


class OcdProductPromo(models.Model):
    _name = "ocd.product.promo"
    _description = "Promo Price Of A Product"
    _order = "date_start desc, id desc"
    _rec_name = "product_tmpl_id"

    product_tmpl_id = fields.Many2one(
        comodel_name="product.template", string="Product", required=True, index=True, ondelete="cascade"
    )
    vendor_id = fields.Many2one(related="product_tmpl_id.ocd_vendor_id", store=True, index=True, string="Vendor")
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="product_tmpl_id.currency_id")
    price = fields.Monetary(string="Promo Price", required=True, currency_field="currency_id")
    reference_price = fields.Monetary(
        string="Price Struck Through", required=True, currency_field="currency_id", readonly=True,
        help="The lowest price of the product in the days before the promo (setting).",
    )
    discount = fields.Integer(string="Discount (%)", compute="_compute_discount", store=True)
    date_start = fields.Datetime(string="From", required=True, index=True, default=fields.Datetime.now)
    date_end = fields.Datetime(string="Until", required=True, index=True)
    source = fields.Selection(
        selection=[("vendor", "Vendor"), ("team", "Team")], string="Put By", required=True, default="vendor",
    )
    active = fields.Boolean(default=True, index=True)
    stopped_at = fields.Datetime(string="Stopped At", readonly=True, copy=False)
    stopped_by_id = fields.Many2one(comodel_name="res.users", string="Stopped By", readonly=True, copy=False)
    stop_reason = fields.Char(string="Why It Stopped", readonly=True, copy=False)
    state = fields.Selection(
        selection=[("scheduled", "To come"), ("running", "Running"), ("ended", "Ended"), ("stopped", "Stopped")],
        compute="_compute_state", string="State",
    )

    @api.depends("price", "reference_price")
    def _compute_discount(self):
        for promo in self:
            reference = promo.reference_price
            promo.discount = round((reference - promo.price) * 100 / reference) if reference else 0

    @api.depends("date_start", "date_end", "active")
    def _compute_state(self):
        now = fields.Datetime.now()
        for promo in self:
            if not promo.active:
                promo.state = "stopped"
            elif promo.date_start and promo.date_start > now:
                promo.state = "scheduled"
            elif promo.date_end and promo.date_end <= now:
                promo.state = "ended"
            else:
                promo.state = "running"

    @api.constrains("price", "reference_price", "date_start", "date_end")
    def _check_promo(self):
        for promo in self:
            if promo.price <= 0:
                raise ValidationError(self.env._("A promo price is above 0."))
            if promo.currency_id.compare_amounts(promo.price, promo.reference_price) >= 0:
                raise ValidationError(self.env._("A promo price is lower than the price struck through."))
            if promo.date_end <= promo.date_start:
                raise ValidationError(self.env._("A promo ends after it starts."))

    @api.depends("product_tmpl_id", "discount")
    def _compute_display_name(self):
        for promo in self:
            promo.display_name = f"{promo.product_tmpl_id.name} · -{promo.discount} %"

    # === WHICH PROMO NOW === #

    @api.model
    def _ocd_priority(self, promo):
        """The promo that wins when two run at once on a product: the one of an evening, then the
        newest (extended by ocd_soirees)."""
        return (0, -promo.id)

    @api.model
    def _ocd_running(self, templates, at=None, order_date=None):
        """{template id: promo} of the promos running at `at` (now). An order started during a
        promo (`order_date`) keeps it a little after its end, while it is paid."""
        if not templates:
            return {}
        now = at or fields.Datetime.now()
        domain = [("product_tmpl_id", "in", templates.ids), ("date_start", "<=", now), ("date_end", ">", now)]
        if order_date and order_date < now:
            # The promos of the date of the order, still within the grace after their end
            domain = [
                ("product_tmpl_id", "in", templates.ids),
                "|", "&", ("date_start", "<=", now), ("date_end", ">", now),
                "&", "&", ("date_start", "<=", order_date), ("date_end", ">", order_date),
                ("date_end", ">", now - PROMO_GRACE),
            ]
        promos = self.sudo().with_context(active_test=True).search(domain)
        best = {}
        for promo in promos:
            current = best.get(promo.product_tmpl_id.id)
            if not current or self._ocd_priority(promo) < self._ocd_priority(current):
                best[promo.product_tmpl_id.id] = promo
        return best

    # === PUT, STOP === #

    @api.model
    def _ocd_limits(self, company=None):
        company = company or self.env.company
        return {
            "discount": company.ocd_promo_max_discount or 50,
            "days": company.ocd_promo_max_days or 30,
            "reference_days": company.ocd_promo_reference_days,
        }

    @api.model
    def _ocd_put(self, product, price, date_end, source="vendor", date_start=None, limits=None, **values):
        """Put `product` (a template) in promo at `price` (in the currency of the company) until
        `date_end`. The rules of OCD Live: lower than the lowest price of the last days, at most the
        discount and the duration set. A promo of the same kind running on it is replaced: one
        promo at a time. Return the promo."""
        product = product.sudo()
        env = self.env
        company = product.company_id or env.company
        limits = limits or self._ocd_limits(company)
        now = fields.Datetime.now()
        date_start = date_start or now
        if product.ocd_vendor_id and product.ocd_review_state != "approved":
            raise UserError(env._("This product is not on sale yet: its promo waits for the check of the team."))
        reference = product._ocd_reference_price()
        currency = product.currency_id
        price = currency.round(price or 0)
        if price <= 0:
            raise UserError(env._("Write the promo price."))
        if currency.compare_amounts(price, reference) >= 0:
            raise UserError(env._(
                "Choose a price under %s: the lowest price of this product in the last %s days.",
                format_amount(env, reference, currency), limits["reference_days"],
            ))
        discount = (reference - price) * 100 / reference
        if discount > limits["discount"] + 0.0001:
            raise UserError(env._("%s %% of discount at most: %s at least.", limits["discount"],
                                  format_amount(env, currency.round(reference * (100 - limits["discount"]) / 100),
                                                currency)))
        if not date_end or date_end <= date_start:
            raise UserError(env._("Choose until when."))
        if source != "evening" and date_end - date_start > timedelta(days=limits["days"], minutes=1):
            raise UserError(env._("%s days at most.", limits["days"]))
        same = self.sudo().search([
            ("product_tmpl_id", "=", product.id), ("source", "=", source), ("date_end", ">", now),
            *(self._ocd_same_domain(values)),
        ])
        if same:
            same._ocd_stop(env._("Replaced by a new promo."))
        return self.sudo().create({
            "product_tmpl_id": product.id,
            "company_id": company.id,
            "price": price,
            "reference_price": reference,
            "date_start": date_start,
            "date_end": date_end,
            "source": source,
            **values,
        })

    @api.model
    def _ocd_same_domain(self, values):
        """The promos replaced by a new one (extended by ocd_soirees: the same evening)."""
        return []

    def _ocd_stop(self, reason=None):
        now = fields.Datetime.now()
        for promo in self.sudo().filtered("active"):
            values = {"active": False, "stopped_at": now, "stop_reason": reason or False}
            if not self.env.user._is_public():
                values["stopped_by_id"] = self.env.uid
            promo.write(values)
        return True

    def action_ocd_stop(self):
        """« Stop the promo » of the team."""
        return self._ocd_stop(self.env._("Stopped by %s.", self.env.user.name))

    # === TEXTS === #

    def _ocd_until_text(self, tz_name=None):
        """« until Sunday 29 November », at the hour of the vendor (or `tz_name`)."""
        self.ensure_one()
        if not tz_name and self.vendor_id:
            tz_name = self.vendor_id._ocd_tz_name()
        local = tools.to_tz(self.date_end - timedelta(seconds=1), tz_name or "Africa/Lome")
        return self.env._("until %s", tools.day_text(self.env, local.date(), "EEEE d MMMM"))

    def _ocd_off_text(self):
        self.ensure_one()
        return f"-{self.discount} %"


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ocd_promo_ids = fields.One2many(comodel_name="ocd.product.promo", inverse_name="product_tmpl_id",
                                    string="Promos")

    def write(self, vals):
        """A price lowered under the price of its promo ends the promo: the new price is lower
        anyway, and a price struck through would no longer be true."""
        result = super().write(vals)
        if "list_price" in vals:
            now = fields.Datetime.now()
            promos = self.env["ocd.product.promo"].sudo().search([
                ("product_tmpl_id", "in", self.ids), ("date_end", ">", now),
            ])
            promos.filtered(
                lambda promo: promo.currency_id.compare_amounts(promo.price, promo.product_tmpl_id.list_price) >= 0
            )._ocd_stop(self.env._("The price of the product went under the price of the promo."))
        return result

    def _ocd_reference_price(self, days=None):
        """The lowest price of the product in the last `days` days (setting), the price of now
        included: the price struck through by a promo. A price raised just before does not make a
        bigger promo."""
        self.ensure_one()
        company = self.company_id or self.env.company
        days = company.ocd_promo_reference_days if days is None else days
        lowest = self.list_price
        if not days:
            return lowest
        since = fields.Datetime.now() - timedelta(days=days)
        lines = self.env["ocd.product.price"].sudo().search(
            [("product_tmpl_id", "=", self.id), ("create_date", ">=", since)], order="create_date, id"
        )
        for index, line in enumerate(lines):
            lowest = min(lowest, line.price)
            # The price held at the start of the period: the one before its first change
            if index == 0 and line.source != "creation" and line.previous_price > 0:
                lowest = min(lowest, line.previous_price)
        return lowest

    def _ocd_promo_ratio(self, promos):
        """{template id: price of the promo / sales price}: the promo applies to the sizes and the
        colours (their extra prices) in the same proportion."""
        ratios = {}
        for template in self:
            promo = promos.get(template.id)
            if promo and template.list_price > 0 and promo.price < template.list_price:
                ratios[template.id] = promo.price / template.list_price
        return ratios

    def _ocd_running_promos(self):
        """The promos running now on these products, or at the date of the order being priced
        (the context of its lines)."""
        if self.env.context.get("ocd_without_promo"):
            return {}
        return self.env["ocd.product.promo"]._ocd_running(
            self, order_date=self.env.context.get("ocd_promo_order_date")
        )

    def _price_compute(self, price_type, uom=None, currency=None, company=None, date=False):
        """Override of `product`: the sales price of a product in promo is its promo price, where
        Odoo computes every price from it (pricelists of the countries, shop, cart, orders)."""
        prices = super()._price_compute(price_type, uom=uom, currency=currency, company=company, date=date)
        if price_type != "list_price" or not self:
            return prices
        ratios = self._ocd_promo_ratio(self._ocd_running_promos())
        for template_id, ratio in ratios.items():
            if template_id in prices:
                prices[template_id] *= ratio
        return prices

    def _ocd_promo_info(self, tz_name=None):
        """{template id: what the pages show of its promo}: the promo, its discount, until when."""
        promos = self.env["ocd.product.promo"]._ocd_running(self)
        return {
            template_id: {"promo": promo, "off": promo._ocd_off_text(), "until": promo._ocd_until_text(tz_name)}
            for template_id, promo in promos.items()
        }

    def _ocd_on_sale_price(self):
        """The price of now in the currency of the company, and the price struck through (False
        without promo): for the pages of the vendor, the control room, the images to share."""
        self.ensure_one()
        promo = self.env["ocd.product.promo"]._ocd_running(self).get(self.id)
        if promo and promo.price < self.list_price:
            return promo.price, promo.reference_price
        return self.list_price, False


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _price_compute(self, price_type, uom=None, currency=None, company=None, date=False):
        """Override of `product`: a variant of a product in promo, at the price of the promo (its
        extra price in the same proportion)."""
        prices = super()._price_compute(price_type, uom=uom, currency=currency, company=company, date=date)
        if price_type != "list_price" or not self:
            return prices
        templates = self.product_tmpl_id
        ratios = templates._ocd_promo_ratio(templates._ocd_running_promos())
        if ratios:
            for product in self:
                ratio = ratios.get(product.product_tmpl_id.id)
                if ratio and product.id in prices:
                    prices[product.id] *= ratio
        return prices
