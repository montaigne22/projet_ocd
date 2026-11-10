from odoo import api, fields, models

def percent_text(percent):
    """Return a price change as shown to the vendors, e.g. "+25 %" or "−15 %"."""
    sign = "+" if percent > 0 else "\u2212"
    return f"{sign}{abs(percent):g}\u202f%"


# Fields of the days of a rule, in the order of date.weekday()
RULE_DAY_FIELDS = ["on_mon", "on_tue", "on_wed", "on_thu", "on_fri", "on_sat", "on_sun"]


class OcdLivePriceRule(models.Model):
    """Price of the hours: a live costs more or less depending on its day and hour, e.g.
    "Saturday 18:00 to 22:00: +25 %" or "Monday morning: -15 %". The change is a percentage of
    the price of one live, so that it stays fair in every currency of the pricelists. The first
    rule of the list that matches a live applies."""

    _name = "ocd.live.price.rule"
    _description = "Price Of The Hours"
    _order = "sequence, id"
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    percent = fields.Float(
        string="Price Change (%)",
        required=True,
        help="+25: the live costs 25 % more. -15: the live costs 15 % less.",
    )
    mode = fields.Selection(
        selection=[("all", "Studio and remote"), ("studio", "At the studio"), ("remote", "Remote")],
        string="Lives",
        required=True,
        default="all",
    )
    hour_from = fields.Float(string="From", default=0.0, help="Hour of the start of the live, studio time.")
    hour_to = fields.Float(string="To", default=24.0)
    date_from = fields.Date(string="Period From", help="Empty: no limit.")
    date_to = fields.Date(string="Period To")
    on_mon = fields.Boolean(string="Monday", default=True)
    on_tue = fields.Boolean(string="Tuesday", default=True)
    on_wed = fields.Boolean(string="Wednesday", default=True)
    on_thu = fields.Boolean(string="Thursday", default=True)
    on_fri = fields.Boolean(string="Friday", default=True)
    on_sat = fields.Boolean(string="Saturday", default=True)
    on_sun = fields.Boolean(string="Sunday", default=True)
    product_tmpl_ids = fields.Many2many(
        comodel_name="product.template",
        string="Packages",
        domain=[("ocd_product_kind", "=", "live_package")],
        help="Empty: all the packages.",
    )

    _check_percent = models.Constraint(
        "CHECK (percent > -100 AND percent <> 0)",
        "The price change is a percentage, not zero, and above -100.",
    )
    _check_hours = models.Constraint(
        "CHECK (hour_from >= 0 AND hour_to <= 24 AND hour_from < hour_to)",
        "The hours of a rule start and end on the same day, and end after they start.",
    )
    _check_dates = models.Constraint(
        "CHECK (date_from IS NULL OR date_to IS NULL OR date_from <= date_to)",
        "The period ends after it starts.",
    )

    @api.model
    def _ocd_rules(self, company):
        """Return the active rules of `company`, in their order."""
        # sudo: read by the public booking pages
        return self.sudo().search([("company_id", "=", company.id)])

    def _ocd_match(self, company, start, mode, product=None):
        """Return the first rule of `self` for a live of `product` starting at `start` (naive
        UTC) in `mode`, or an empty recordset."""
        local = company._ocd_to_local(start)
        day = local.date()
        hour = local.hour + local.minute / 60
        template = product.product_tmpl_id if product else None
        for rule in self:
            if not rule[RULE_DAY_FIELDS[day.weekday()]]:
                continue
            if not rule.hour_from <= hour < rule.hour_to:
                continue
            if (rule.date_from and day < rule.date_from) or (rule.date_to and day > rule.date_to):
                continue
            if rule.mode != "all" and rule.mode != mode:
                continue
            if rule.product_tmpl_ids and template and template not in rule.product_tmpl_ids:
                continue
            return rule
        return self.browse()

    @api.model
    def _ocd_percent(self, company, start, mode, product=None):
        """Return the price change (%) of a live, 0 when no rule applies."""
        return self._ocd_rules(company)._ocd_match(company, start, mode, product).percent or 0.0
