from odoo import fields, models

DELIVERY_MODES = [
    ("vendor", "The vendor delivers"),
    ("pickup", "An OCD courier picks it up at the vendor"),
    ("stock", "From the OCD stock"),
]

PAYOUT_FREQUENCIES = [
    ("daily", "Every day"),
    ("weekly", "Every week"),
    ("biweekly", "Every two weeks"),
    ("monthly", "Every month"),
]

WEEKDAYS = [
    ("0", "Monday"),
    ("1", "Tuesday"),
    ("2", "Wednesday"),
    ("3", "Thursday"),
    ("4", "Friday"),
    ("5", "Saturday"),
    ("6", "Sunday"),
]


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_default_commission = fields.Float(string="Default Commission (%)", default=15.0)
    ocd_default_delivery_mode = fields.Selection(
        selection=DELIVERY_MODES, string="Who Delivers By Default", default="pickup"
    )
    ocd_prep_hours = fields.Integer(
        string="Time To Prepare A Parcel (Hours)",
        default=4,
        help="Past this time, the vendor is reminded.",
    )
    ocd_escalation_hours = fields.Integer(
        string="Alert The Dispatch After The Reminder (Hours)",
        default=2,
    )
    ocd_code_max_attempts = fields.Integer(string="Wrong Codes Before Locking", default=3)
    ocd_max_failed_attempts = fields.Integer(string="Failed Attempts Before Return", default=2)
    ocd_vendor_rate_min = fields.Monetary(
        string="Lowest Delivery Price Of A Vendor",
        currency_field="currency_id",
        help="The vendors who deliver set their prices between this amount and the highest one. "
        "0: no limit.",
    )
    ocd_vendor_rate_max = fields.Monetary(
        string="Highest Delivery Price Of A Vendor",
        currency_field="currency_id",
        help="0: no limit.",
    )
    ocd_delivery_commission = fields.Float(
        string="Share Of OCD On The Deliveries Of The Vendors (%)",
        default=0.0,
        help="Part of the delivery price kept by OCD Live when the vendor delivers. The deliveries "
        "of the OCD couriers and of the travel agencies are kept by OCD Live.",
    )
    ocd_stock_city_id = fields.Many2one(
        comodel_name="res.city",
        string="City Of The OCD Stock",
        help="The parcels of the OCD stock leave from this city: the rates of OCD Live from this "
        "city are used for them.",
    )
    ocd_return_days = fields.Integer(
        string="Days To Ask For A Return",
        default=30,
        help="After the delivery, the customer can ask for a return from the tracking page during "
        "these days. 0: no return from the website.",
    )
    ocd_cash_deadline = fields.Float(
        string="Cash Handed Over Before",
        default=20.0,
        help="Hour of the studio time zone before which the couriers hand over the cash.",
    )
    ocd_cod_cash = fields.Boolean(string="Cash At The Door", default=True)
    ocd_cod_online = fields.Boolean(
        string="Payment On The Phone Of The Customer",
        default=True,
        help="At the door, the courier shows a QR code: the customer pays on the phone with "
        "the payment methods offered in the country of the customer (Mobile Money, card...). "
        "The payment is confirmed by the provider.",
    )
    ocd_cod_momo_declared = fields.Boolean(
        string="Mobile Money Declared By The Courier",
        default=False,
        help="The customer pays to the Mobile Money number of OCD and the courier types the "
        "reference of the payment, checked by the team.",
    )
    ocd_default_payout_frequency = fields.Selection(
        selection=PAYOUT_FREQUENCIES, string="Default Payout Rhythm", default="weekly"
    )
    ocd_payout_weekday = fields.Selection(selection=WEEKDAYS, string="Payout Day", default="0")
    ocd_payout_min_amount = fields.Float(
        string="Minimum Payout",
        default=1000.0,
        help="Below this amount, the payout waits for the next period.",
    )
    ocd_payout_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Payout Journal",
        domain="[('type', 'in', ('bank', 'cash'))]",
        help="Journal of the payments of the payouts. By default, the first bank journal.",
    )
    ocd_deliveries_channel_id = fields.Many2one(
        comodel_name="discuss.channel",
        string="Team Channel For Deliveries",
    )

    def _ocd_vendor_rate_bounds(self):
        """(lowest, highest) price of a delivery of a vendor; 0 means no limit."""
        self.ensure_one()
        return self.ocd_vendor_rate_min or 0.0, self.ocd_vendor_rate_max or 0.0

