import logging
import secrets
from datetime import timedelta

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import consteq

from odoo.addons.ocd_live.tools import day_text

from .res_company import PARTS
from .res_partner import ACTIVITY_CHECK, phone_digits

_logger = logging.getLogger(__name__)

CONTENT_MAX = 120
NAME_MAX = 60
LANDMARK_MAX = 120
NOTE_MAX = 500
RETURN_CODE_ATTEMPTS = 3
CONFIRM_STATES = [
    ("waiting", "Not answered"),
    ("confirmed", "Confirmed"),
    ("moved", "Another time"),
    ("not_for_me", "Not for them"),
]
CHECK_STATES = [("to_check", "To check"), ("ok", "Checked"), ("refused", "Refused")]
RETURN_STATES = [("to_return", "To give back"), ("handed_back", "Given back")]
CLAIM_STATES = [
    ("open", "Problem reported"),
    ("customer_right", "The customer was right"),
    ("sender_right", "The sender was right"),
]
ACTIVITY_REFUND = "ocd_live_shop.mail_activity_type_refund"


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ocd_express = fields.Boolean(string="OCD Express", copy=False, index=True, readonly=True)
    ocd_express_sender_id = fields.Many2one(
        comodel_name="res.partner", string="Sender", copy=False, index="btree_not_null", readonly=True,
    )
    ocd_express_content = fields.Char(string="In The Parcel", copy=False)
    ocd_express_value = fields.Monetary(
        string="Declared Value", copy=False, currency_field="ocd_currency_id",
        help="What OCD pays back when it loses or damages the parcel: the money to collect, or the value "
        "written for a parcel already paid.",
    )
    ocd_express_fee = fields.Monetary(string="Price Of The Delivery", copy=False, currency_field="ocd_currency_id")
    ocd_express_fee_by = fields.Selection(
        selection=[("sender", "The sender"), ("customer", "The customer")], string="Delivery Paid By",
        copy=False, default="sender",
    )
    ocd_express_can_open = fields.Boolean(string="May Open Before Paying", copy=False, default=True)
    ocd_express_dropoff = fields.Boolean(
        string="Dropped At The OCD Point", copy=False,
        help="The sender drops the parcel at the OCD point: no pick-up.",
    )
    ocd_express_pickup_id = fields.Many2one(
        comodel_name="ocd.express.pickup", string="Pick-Up", copy=False, index="btree_not_null", ondelete="set null",
    )
    ocd_express_deliver_on = fields.Date(string="To Deliver On", copy=False, index=True)
    ocd_express_deliver_part = fields.Selection(selection=PARTS, string="Part Of The Day", copy=False)
    ocd_express_check = fields.Selection(selection=CHECK_STATES, string="Team Check", copy=False, tracking=True)
    ocd_express_check_reason = fields.Char(string="Why It Is Checked", copy=False)
    ocd_express_confirm = fields.Selection(
        selection=CONFIRM_STATES, string="Answer Of The Customer", copy=False, default="waiting", tracking=True,
    )
    ocd_express_latitude = fields.Float(string="Latitude", copy=False, digits=(10, 7))
    ocd_express_longitude = fields.Float(string="Longitude", copy=False, digits=(10, 7))
    ocd_express_token = fields.Char(string="Tracking Token", copy=False, groups="base.group_system")
    ocd_express_not_taken = fields.Char(string="Not Taken At The Pick-Up", copy=False)
    ocd_express_return_state = fields.Selection(
        selection=RETURN_STATES, string="Return", copy=False, tracking=True, index="btree_not_null",
    )
    ocd_express_return_code = fields.Char(string="Return Code", copy=False, groups="base.group_system")
    ocd_express_return_attempts = fields.Integer(string="Wrong Return Codes", copy=False)
    ocd_express_returned_at = fields.Datetime(string="Given Back At", copy=False)
    ocd_express_claim_state = fields.Selection(
        selection=CLAIM_STATES, string="Problem After The Delivery", copy=False, tracking=True,
        index="btree_not_null",
    )
    ocd_express_claim_note = fields.Text(string="Problem Reported", copy=False)
    ocd_express_claim_at = fields.Datetime(string="Reported At", copy=False)
    ocd_express_lost = fields.Boolean(string="Lost Or Damaged By OCD", copy=False, tracking=True)
    ocd_express_anonymized = fields.Boolean(string="Customer Erased", copy=False)
    ocd_express_money_state = fields.Selection(
        selection=[("waiting", "Waits for the money"), ("counted", "Counted for the sender")],
        string="Money Of The Sender", compute="_compute_ocd_express_money_state",
    )

    @api.depends("ocd_vendor_bill_ids.ocd_express_kind")
    def _compute_ocd_express_money_state(self):
        for picking in self:
            if not picking.ocd_express:
                picking.ocd_express_money_state = False
                continue
            settled = picking.ocd_vendor_bill_ids.filtered(lambda m: m.ocd_express_kind in ("collected", "fees"))
            picking.ocd_express_money_state = "counted" if settled else "waiting"

    @api.depends("ocd_express_fee", "ocd_express_fee_by")
    def _compute_ocd_fee_amount(self):
        """Override of `ocd_live_shop`: the delivery of a parcel of OCD Express is in the money
        to collect when the customer pays it."""
        express = self.filtered("ocd_express")
        for picking in express:
            picking.ocd_fee_amount = picking.ocd_express_fee if picking.ocd_express_fee_by == "customer" else 0.0
        super(StockPicking, self - express)._compute_ocd_fee_amount()

    # === CREATION === #

    @api.model
    def _ocd_express_picking_type(self):
        return self.env.ref("ocd_express.picking_type_express").sudo()

    @api.model
    def _ocd_express_destination(self, district, city):
        """(district, city, by agency, rate) of an address of a customer: a district of a city open
        to OCD Express (its courier), or another city by travel agency."""
        company = self.env.company
        city = district.city_id if district else city
        if not city:
            raise UserError(self.env._("Choose the city and the district of your customer."))
        if city in company.ocd_express_city_ids:
            if not district:
                raise UserError(self.env._("Choose the district of your customer."))
            return district, city, False
        return self.env["res.city.district"], city, True

    @api.model
    def _ocd_express_rate(self, sender, recipient, by_agency):
        """The rate of OCD Live for the parcel: its courier in the city, a travel agency elsewhere."""
        company = self.env.company
        Rate = self.env["ocd.delivery.rate"].sudo()
        origin_city = sender.city_id or sender.district_id.city_id or company.ocd_express_city_ids[:1]
        origin = (origin_city.country_id or company.country_id, origin_city)
        operator = "agency" if by_agency else "courier"
        rates = Rate._ocd_rates(company).filtered(lambda r: not r.vendor_id and r.operator == operator)
        rate = rates._ocd_best(recipient, origin)
        if not rate:
            raise UserError(self.env._(
                "OCD Express does not deliver to %s yet.", recipient.district_id.name or recipient.city_id.name or "-"))
        return rate, rate._ocd_converted_price(company.currency_id, company, fields.Date.context_today(self))

    @api.model
    def _ocd_express_values(self, sender, data, parcel=None):
        """Check what the sender typed (`data`: name, phone, district, city, landmark, content,
        prepaid, amount, value, fee_by, can_open, consent, dropoff) and return the values of the
        parcel and of its customer, the reason why the team checks it (or False)."""
        _ = self.env._
        company = self.env.company
        currency = company.currency_id
        if sender.ocd_express_state != "active":
            raise UserError(_("Your account of OCD Express is not open: write to OCD Live."))
        if not data.get("consent"):
            raise UserError(_("Tick that your customer agrees to receive the messages of OCD Express."))
        name = (data.get("name") or "").strip()[:NAME_MAX]
        phone = data.get("phone")
        content = (data.get("content") or "").strip()[:CONTENT_MAX]
        if not name:
            raise UserError(_("Write the name of your customer."))
        if not phone:
            raise UserError(_("Write the WhatsApp number of your customer."))
        if phone_digits(phone) == phone_digits(sender.phone):
            raise UserError(_("This is your own number: write the number of your customer."))
        if not content:
            raise UserError(_("Write what is in the parcel."))
        district, city, by_agency = self._ocd_express_destination(data.get("district"), data.get("city"))
        prepaid = bool(data.get("prepaid"))
        fee_by = "customer" if data.get("fee_by") == "customer" else "sender"
        amount = 0.0 if prepaid else currency.round(float(data.get("amount") or 0.0))
        value = currency.round(float(data.get("value") or 0.0)) if prepaid else amount
        if by_agency and (not prepaid or fee_by == "customer"):
            raise UserError(_(
                "Towards %s, the parcel goes by travel agency: paid in advance, nothing to collect at the door.",
                city.name))
        if not prepaid and currency.compare_amounts(amount, 0.0) <= 0:
            raise UserError(_("Write the amount your customer pays at the door, or choose « Already paid »."))
        if currency.compare_amounts(amount, 0.0) < 0 or currency.compare_amounts(value, 0.0) < 0:
            raise UserError(_("An amount cannot be negative."))
        recipient_vals = {
            "name": name,
            "phone": phone,
            "country_id": (city.country_id or company.country_id).id,
            "city_id": city.id,
            "city": city.name,
            "district_id": district.id or False,
            "delivery_landmark": (data.get("landmark") or "").strip()[:LANDMARK_MAX] or False,
            "ocd_express_recipient": True,
        }
        probe = self.env["res.partner"].new(recipient_vals)
        rate, fee = self._ocd_express_rate(sender, probe, by_agency)
        if fee_by == "sender" and currency.compare_amounts(
                sender._ocd_express_debt(), company.ocd_express_debt_max) > 0 and company.ocd_express_debt_max:
            raise UserError(_(
                "You owe %(amount)s to OCD: pay it on « My money », or let your customer pay the delivery.",
                amount=self.env["ocd.express.pickup"]._ocd_money(sender._ocd_express_debt())))
        cod = amount + (fee if fee_by == "customer" else 0.0)
        reason = self._ocd_express_check_reason(sender, amount, parcel)
        values = {
            "ocd_express_content": content,
            "ocd_express_value": value,
            "ocd_express_fee": fee,
            "ocd_express_fee_by": fee_by,
            "ocd_express_can_open": bool(data.get("can_open")),
            "ocd_goods_amount": amount,
            "ocd_cod_state": "to_collect" if currency.compare_amounts(cod, 0.0) > 0 else "none",
            "ocd_rate_id": rate.id,
            "ocd_by_agency": by_agency,
        }
        return values, recipient_vals, reason

    @api.model
    def _ocd_express_check_reason(self, sender, amount, parcel=None):
        """Why the team checks the parcel before it leaves (False: it leaves)."""
        _ = self.env._
        company = self.env.company
        currency = company.currency_id
        Pickup = self.env["ocd.express.pickup"]
        if currency.compare_amounts(amount, sender.ocd_express_max_cod) > 0:
            return _("Above the limit of the sender (%s)", Pickup._ocd_money(sender.ocd_express_max_cod))
        today = company._ocd_local_today()
        start = company._ocd_express_part_start(today, "morning") - timedelta(hours=8)
        others = self.sudo().search([
            ("ocd_express", "=", True), ("ocd_express_sender_id", "=", sender.id),
            ("create_date", ">=", start), ("ocd_stage", "!=", "cancelled"),
            *([("id", "!=", parcel.id)] if parcel else []),
        ])
        if company.ocd_express_id_daily and not sender.ocd_express_id_checked:
            total = sum(others.mapped("ocd_goods_amount")) + amount
            if currency.compare_amounts(total, company.ocd_express_id_daily) > 0:
                return _("More than %s to collect today: check the identity of the sender",
                         Pickup._ocd_money(company.ocd_express_id_daily))
        if company.ocd_express_first_day_max and (sender.ocd_express_since or today) >= today \
                and len(others) >= company.ocd_express_first_day_max:
            return _("New sender: more than %s parcels on the first day", company.ocd_express_first_day_max)
        return False

    @api.model
    def _ocd_express_create(self, sender, data):
        """Create the parcel of OCD Express of `sender` from what they typed. Return it."""
        values, recipient_vals, reason = self._ocd_express_values(sender, data)
        company = self.env.company
        # A number that said « Not for me » receives no message of OCD Express any more
        recipient_vals["ocd_express_optout"] = self._ocd_express_opted_out(recipient_vals["phone"])
        recipient = self.env["res.partner"].sudo().create(self._ocd_express_recipient_values(recipient_vals))
        picking_type = self._ocd_express_picking_type()
        parcel = self.sudo().create({
            "picking_type_id": picking_type.id,
            "location_id": picking_type.default_location_src_id.id,
            "location_dest_id": picking_type.default_location_dest_id.id,
            "partner_id": recipient.id,
            "company_id": company.id,
            "origin": sender.name,
            "ocd_is_parcel": True,
            "ocd_express": True,
            "ocd_express_sender_id": sender.id,
            "ocd_delivery_mode": "pickup",
            "ocd_stage": "to_prepare" if reason else "ready",
            "ocd_ready_at": False if reason else fields.Datetime.now(),
            "ocd_express_dropoff": bool(data.get("dropoff")),
            "ocd_express_check": "to_check" if reason else "ok",
            "ocd_express_check_reason": reason or False,
            "ocd_express_token": secrets.token_urlsafe(16),
            "move_ids": [Command.create({
                "product_id": self.env.ref("ocd_express.product_express_parcel").product_variant_id.id,
                "product_uom_qty": 1,
                "description_picking": values["ocd_express_content"],
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
            })],
            **values,
        })
        parcel.action_confirm()
        if reason:
            parcel._ocd_alert(self.env._(
                "Parcel %(parcel)s of %(sender)s to check: %(reason)s.",
                parcel=parcel.name, sender=sender.name, reason=reason), ACTIVITY_CHECK)
        else:
            parcel._ocd_express_plan()
        parcel._ocd_express_notify("created")
        return parcel

    @api.model
    def _ocd_express_opted_out(self, phone):
        digits = phone_digits(phone)
        if len(digits) < 8:
            return False
        refused = self.env["res.partner"].sudo().search(
            [("ocd_express_optout", "=", True), ("phone", "!=", False)])
        return any(phone_digits(partner.phone)[-9:] == digits[-9:] for partner in refused)

    def _ocd_express_update(self, data):
        """The sender changes the parcel before it is picked up."""
        self.ensure_one()
        if not self._ocd_express_editable():
            raise UserError(self.env._("The parcel %s already left: it cannot be changed.", self.name))
        values, recipient_vals, reason = self._ocd_express_values(self.ocd_express_sender_id, data, parcel=self)
        recipient_vals.pop("ocd_express_recipient")
        self.partner_id.sudo().write(recipient_vals)
        self.move_ids.write({"description_picking": values["ocd_express_content"]})
        dropoff = bool(data.get("dropoff"))
        moved = dropoff != self.ocd_express_dropoff
        self.sudo().write(dict(values, ocd_express_dropoff=dropoff))
        if reason and self.ocd_express_check != "to_check":
            self.sudo().write({
                "ocd_express_check": "to_check", "ocd_express_check_reason": reason,
                "ocd_stage": "to_prepare", "ocd_courier_id": False, "ocd_express_pickup_id": False,
            })
            self._ocd_alert(self.env._("Parcel %(parcel)s changed, to check: %(reason)s.",
                                       parcel=self.name, reason=reason), ACTIVITY_CHECK)
        elif moved and self.ocd_express_check == "ok":
            self.sudo().ocd_express_pickup_id = False
            self._ocd_express_plan()
        self.message_post(body=self.env._("Changed by the sender."))
        return True

    def _ocd_express_editable(self):
        self.ensure_one()
        return self.ocd_express and self.ocd_stage in ("to_prepare", "ready") and not self.ocd_picked_at

    def _ocd_express_plan(self, moment=None):
        """Give the parcel its slot (the next wave with room) and its pick-up passage at the
        sender, with the courier of the passage."""
        company = self.env.company
        for parcel in self.sudo():
            pickup_day, part, deliver_on, deliver_part = company._ocd_express_plan(moment)
            vals = {"ocd_express_deliver_on": deliver_on, "ocd_express_deliver_part": deliver_part}
            if parcel.ocd_express_dropoff:
                vals.update({"ocd_express_pickup_id": False, "ocd_courier_id": False})
            else:
                pickup = self.env["ocd.express.pickup"]._ocd_for(parcel.ocd_express_sender_id, pickup_day, part)
                vals.update({"ocd_express_pickup_id": pickup.id, "ocd_courier_id": pickup.courier_id.id})
            parcel.write(vals)

    def _ocd_express_replan(self):
        """A parcel not taken at its pick-up: the next slot."""
        company = self.env.company
        for parcel in self.sudo():
            pickup = parcel.ocd_express_pickup_id
            if pickup:
                pickup_day, part, deliver_on, deliver_part = company._ocd_express_next_slot(pickup.date, pickup.part)
                if pickup_day < company._ocd_local_today():
                    pickup_day, part, deliver_on, deliver_part = company._ocd_express_plan()
                following = self.env["ocd.express.pickup"]._ocd_for(parcel.ocd_express_sender_id, pickup_day, part)
                parcel.write({
                    "ocd_express_pickup_id": following.id, "ocd_courier_id": following.courier_id.id,
                    "ocd_express_deliver_on": deliver_on, "ocd_express_deliver_part": deliver_part,
                })
            else:
                parcel._ocd_express_plan()

    # === THE TEAM === #

    def _ocd_express_check_team(self):
        if not self.env.user.has_group("ocd_live.group_ocd_live_user"):
            raise AccessError(self.env._("Only the team of OCD Live checks the parcels of OCD Express."))

    def action_ocd_express_approve(self):
        """The team checked the parcel: it leaves with the next pick-up."""
        self._ocd_express_check_team()
        for parcel in self.filtered(lambda p: p.ocd_express and p.ocd_express_check == "to_check"):
            parcel.sudo().write({
                "ocd_express_check": "ok", "ocd_stage": "ready", "ocd_ready_at": fields.Datetime.now(),
            })
            parcel.activity_feedback([ACTIVITY_CHECK])
            parcel._ocd_express_plan()
            parcel.message_post(body=self.env._("Checked by %s.", self.env.user.name))
        return True

    def action_ocd_express_refuse(self, reason=None):
        self._ocd_express_check_team()
        for parcel in self.filtered(lambda p: p.ocd_express and p.ocd_express_check == "to_check"):
            parcel.sudo().write({"ocd_express_check": "refused"})
            parcel.activity_feedback([ACTIVITY_CHECK])
            parcel._ocd_express_cancel(self.env._("Refused by the team: %s", reason.name) if reason
                                       else self.env._("Refused by the team."))
            parcel._ocd_express_notify("refused")
        return True

    def action_ocd_express_received(self):
        """The parcel dropped by the sender arrived at the OCD point: a courier takes it."""
        self._ocd_express_check_team()
        for parcel in self.filtered(lambda p: p.ocd_express and p.ocd_stage == "ready" and p.ocd_express_dropoff):
            courier = parcel.ocd_courier_id or self.env["res.partner"].sudo()._ocd_find_courier(
                parcel.partner_id.district_id)
            parcel.sudo().write({"ocd_courier_id": courier.id})
            parcel.action_ocd_pick_up()
            parcel.message_post(body=self.env._("Received at the OCD point by %s.", self.env.user.name))
        return True

    def _ocd_express_check_manager(self):
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only a manager of OCD Live settles the money of OCD Express."))

    def action_ocd_express_lost(self, amount=None, note=None):
        """Lost or damaged by OCD: OCD pays the declared value back to the sender, at most the
        amount of the settings."""
        self._ocd_express_check_manager()
        for parcel in self.filtered(lambda p: p.ocd_express and not p.ocd_express_lost):
            company = parcel.company_id
            limit = company.ocd_express_lost_max
            value = parcel.ocd_express_value if amount is None else amount
            value = min(value, limit) if limit else value
            if parcel.ocd_stage in ("delivered",):
                raise UserError(self.env._("The parcel %s was delivered with its code.", parcel.name))
            parcel.sudo().ocd_express_lost = True
            if company.currency_id.compare_amounts(value, 0.0) > 0:
                self._ocd_express_move(parcel.ocd_express_sender_id, "in_invoice", "lost", [(
                    "ocd_express.product_express_lost",
                    self.env._("Parcel %s lost or damaged by OCD", parcel.name), value)], parcel=parcel)
            if parcel.ocd_stage not in ("cancelled", "returned"):
                parcel._ocd_express_cancel(self.env._("Lost or damaged by OCD: %s", note or "-"))
            parcel.message_post(body=self.env._("Lost or damaged by OCD: %(amount)s paid back to the sender. %(note)s",
                                                amount=value, note=note or ""))
        return True

    def action_ocd_express_claim_customer(self, amount=None):
        """The customer was right: the amount goes back to them and the sender owes it."""
        self._ocd_express_check_manager()
        for parcel in self.filtered(lambda p: p.ocd_express and p.ocd_express_claim_state == "open"):
            value = parcel.ocd_goods_amount if amount is None else amount
            parcel.sudo().ocd_express_claim_state = "customer_right"
            parcel.activity_feedback([ACTIVITY_CHECK])
            if parcel.company_id.currency_id.compare_amounts(value, 0.0) > 0:
                self._ocd_express_move(parcel.ocd_express_sender_id, "in_refund", "claim", [(
                    "ocd_express.product_express_claim",
                    self.env._("Problem with %s: paid back to the customer", parcel.name), value)], parcel=parcel)
                parcel._ocd_alert(self.env._(
                    "Pay %(amount)s back to %(customer)s for the parcel %(parcel)s.",
                    amount=value, customer=parcel.partner_id.name, parcel=parcel.name), ACTIVITY_REFUND)
            parcel._ocd_express_notify("claim_closed")
        return True

    def action_ocd_express_claim_sender(self):
        """The sender was right: their money leaves with the next payout."""
        self._ocd_express_check_manager()
        for parcel in self.filtered(lambda p: p.ocd_express and p.ocd_express_claim_state == "open"):
            parcel.sudo().ocd_express_claim_state = "sender_right"
            parcel.activity_feedback([ACTIVITY_CHECK])
            parcel._ocd_express_notify("claim_closed")
        return True

    # === THE SENDER === #

    def _ocd_express_cancel(self, note):
        """Cancel the parcel (not picked up yet, refused by the team, lost)."""
        for parcel in self.sudo():
            pickup = parcel.ocd_express_pickup_id
            parcel.write({"ocd_stage": "cancelled", "ocd_express_pickup_id": False, "ocd_courier_id": False})
            if parcel.state not in ("done", "cancel"):
                parcel.action_cancel()
            parcel.message_post(body=note)
            if pickup and not pickup.parcel_ids and pickup.state == "planned":
                pickup.state = "cancelled"

    def _ocd_express_cancel_by_sender(self):
        self.ensure_one()
        if not self._ocd_express_editable():
            raise UserError(self.env._("The parcel %s already left: it cannot be cancelled.", self.name))
        self._ocd_express_cancel(self.env._("Cancelled by the sender."))
        self._ocd_express_notify("cancelled")
        return True

    def _ocd_express_return_code(self):
        """The return code the sender gives to the courier who brings the parcel back."""
        self.ensure_one()
        return self.sudo().ocd_express_return_code or ""

    def _ocd_express_hand_back(self, code, courier):
        """The courier gives the returned parcel back to the sender, against their return code.
        Return (given back, attempts left): a wrong code is counted, never raised (the count
        stays)."""
        self.ensure_one()
        if not self.ocd_express or self.ocd_express_return_state != "to_return":
            raise UserError(self.env._("The parcel %s is not to give back.", self.name))
        if self.ocd_courier_id != courier:
            raise UserError(self.env._("Another courier gives this parcel back."))
        if self.ocd_express_return_attempts >= RETURN_CODE_ATTEMPTS:
            raise UserError(self.env._("Too many wrong return codes: call the team."))
        expected = self._ocd_express_return_code()
        if expected and code and consteq((code or "").strip(), expected):
            self._ocd_express_handed_back()
            return True, 0
        attempts = self.ocd_express_return_attempts + 1
        self.sudo().ocd_express_return_attempts = attempts
        if attempts >= RETURN_CODE_ATTEMPTS:
            self._ocd_alert(self.env._(
                "Return of %(parcel)s blocked after %(count)s wrong codes.", parcel=self.name, count=attempts),
                ACTIVITY_CHECK)
        return False, max(RETURN_CODE_ATTEMPTS - attempts, 0)

    def _ocd_express_handed_back(self):
        for parcel in self.sudo():
            parcel.write({"ocd_express_return_state": "handed_back", "ocd_express_returned_at": fields.Datetime.now()})
            if parcel.state not in ("done", "cancel"):
                parcel.action_cancel()
            fee = parcel.company_id.ocd_express_return_fee
            if parcel.company_id.currency_id.compare_amounts(fee, 0.0) > 0 and not parcel.ocd_express_lost:
                self._ocd_express_move(parcel.ocd_express_sender_id, "in_refund", "return", [(
                    "ocd_express.product_express_return", self.env._("Return of %s", parcel.name), fee)], parcel=parcel)
            parcel.message_post(body=self.env._("Given back to the sender."))
            parcel._ocd_express_notify("handed_back")

    # === THE CUSTOMER WHO RECEIVES === #

    def _ocd_express_check_token(self, token):
        self.ensure_one()
        expected = self.sudo().ocd_express_token or ""
        return bool(self.ocd_express and expected and token and consteq(expected, token))

    def _ocd_express_tracking_url(self):
        self.ensure_one()
        return f"{self.get_base_url()}/{self._ocd_tracking_path()}"

    def _ocd_tracking_path(self):
        """Override of `ocd_live_shop`: the page of the customer of a parcel of OCD Express."""
        self.ensure_one()
        if self.ocd_express:
            return f"express/suivi/{self.id}/{self.sudo().ocd_express_token}"
        return super()._ocd_tracking_path()

    def _ocd_express_customer_open(self):
        """Whether the customer may still answer (confirm, another time, not for them)."""
        self.ensure_one()
        return self.ocd_stage in ("to_prepare", "ready", "picked", "on_the_way", "problem")

    def _ocd_express_confirm(self):
        self.ensure_one()
        if not self._ocd_express_customer_open():
            raise UserError(self.env._("This parcel is no longer on its way."))
        self.sudo().ocd_express_confirm = "confirmed"
        return True

    def _ocd_express_move_to(self, day, part):
        """The customer chooses another time: the parcel is delivered then (a second passage
        after a failed one)."""
        self.ensure_one()
        company = self.company_id
        today = company._ocd_local_today()
        if not self._ocd_express_customer_open() or self.ocd_stage == "on_the_way":
            raise UserError(self.env._("The courier is on the way: call them."))
        if part not in dict(PARTS) or day < today or day > today + timedelta(days=7):
            raise UserError(self.env._("Choose a time in the next days."))
        self.sudo().write({"ocd_express_deliver_on": day, "ocd_express_deliver_part": part,
                           "ocd_express_confirm": "moved"})
        if self.ocd_stage == "problem":
            self.action_ocd_retry()
            self.message_post(body=self.env._("Second passage asked by the customer."))
        self._ocd_express_notify("moved")
        return True

    def _ocd_express_not_for_me(self):
        """« Not for me »: no message of OCD Express goes to this number any more, and the
        parcel goes back to its sender."""
        self.ensure_one()
        if not self._ocd_express_customer_open():
            raise UserError(self.env._("This parcel is no longer on its way."))
        Partner = self.env["res.partner"].sudo()
        digits = phone_digits(self.partner_id.phone)
        same = Partner.search([("ocd_express_recipient", "=", True), ("phone", "!=", False)]).filtered(
            lambda p: phone_digits(p.phone) == digits)
        (same | self.partner_id).write({"ocd_express_optout": True})
        self.sudo().ocd_express_confirm = "not_for_me"
        if self.ocd_stage in ("to_prepare", "ready"):
            self._ocd_express_cancel(self.env._("The customer said it is not for them."))
            self._ocd_express_notify("not_for_me")
        else:
            self._ocd_return("returned")
        return True

    def _ocd_express_set_position(self, latitude, longitude):
        self.ensure_one()
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or (latitude == 0 and longitude == 0):
            raise UserError(self.env._("The position of the phone could not be read."))
        if not self._ocd_express_customer_open():
            raise UserError(self.env._("This parcel is no longer on its way."))
        self.sudo().write({"ocd_express_latitude": latitude, "ocd_express_longitude": longitude})
        return True

    def _ocd_express_claim_open(self):
        """Whether the customer may still report a problem with the parcel."""
        self.ensure_one()
        hours = self.company_id.ocd_express_claim_hours
        return bool(
            self.ocd_express and self.ocd_stage == "delivered" and not self.ocd_express_claim_state and hours
            and self.ocd_delivered_at and self.ocd_delivered_at > fields.Datetime.now() - timedelta(hours=hours)
        )

    def _ocd_express_report_claim(self, note):
        self.ensure_one()
        note = (note or "").strip()[:NOTE_MAX]
        if not self._ocd_express_claim_open():
            raise UserError(self.env._("A problem is reported within %s hours of the delivery.",
                                       self.company_id.ocd_express_claim_hours))
        if not note:
            raise UserError(self.env._("Write what is wrong with the parcel."))
        self.sudo().write({
            "ocd_express_claim_state": "open", "ocd_express_claim_note": note,
            "ocd_express_claim_at": fields.Datetime.now(),
        })
        self._ocd_alert(self.env._(
            "%(customer)s reports a problem with the parcel %(parcel)s of %(sender)s: %(note)s",
            customer=self.partner_id.name, parcel=self.name, sender=self.ocd_express_sender_id.name, note=note),
            ACTIVITY_CHECK)
        self._ocd_express_notify("claim")
        return True

    # === STEPS OF THE SHOP === #

    def action_ocd_leave(self):
        """Override of `ocd_live_shop`: a parcel of OCD Express leaves once picked up (or
        received at the OCD point) and checked by the team when it had to be."""
        for parcel in self.filtered("ocd_express"):
            if parcel.ocd_express_check == "to_check":
                raise UserError(self.env._("The team checks the parcel %s first.", parcel.name))
            if parcel.ocd_stage == "ready":
                raise UserError(self.env._("Pick the parcel %s up first.", parcel.name))
        return super().action_ocd_leave()

    def _ocd_allowed_cod_methods(self, collector):
        """Override of `ocd_live_shop`: for OCD Express, never a Mobile Money « declared » (a
        reference typed by the courier is not enough), and only on the phone of the customer
        above the amount of the settings."""
        methods = super()._ocd_allowed_cod_methods(collector)
        if not self.ocd_express:
            return methods
        methods = [method for method in methods if method != "momo_declared"]
        limit = self.company_id.ocd_express_online_above
        if limit and self.company_id.currency_id.compare_amounts(self.ocd_cod_amount, limit) > 0:
            methods = [method for method in methods if method == "online"]
        return methods

    def _ocd_collect(self, method, collector, reference=False):
        """Override of `ocd_live_shop`: the cash on a courier is capped (their safety)."""
        if self.ocd_express and method == "cash" and collector.ocd_is_courier:
            limit = self.company_id.ocd_express_cash_max
            currency = self.company_id.currency_id
            collector.invalidate_recordset(["ocd_cash_on_hand"])
            if limit and currency.compare_amounts(collector.ocd_cash_on_hand + self.ocd_cod_amount, limit) > 0:
                raise UserError(self.env._(
                    "You already carry %(cash)s: drop your cash at the OCD point first, or let the customer pay "
                    "on their phone.", cash=self.env["ocd.express.pickup"]._ocd_money(collector.ocd_cash_on_hand)))
        return super()._ocd_collect(method, collector, reference=reference)

    def _ocd_deliver(self):
        """Override of `ocd_live_shop`: the money of the sender counts once it reached OCD."""
        result = super()._ocd_deliver()
        express = self.filtered("ocd_express")
        express._ocd_express_settle()
        express._ocd_express_notify("delivered")
        return result

    def _ocd_cash_remitted(self):
        """Override of `ocd_live_shop`: the cash of a parcel of OCD Express reached the cash desk."""
        super()._ocd_cash_remitted()
        self.filtered(lambda p: p.ocd_express and p.ocd_stage == "delivered")._ocd_express_settle()

    def _ocd_report_problem(self, reason, note=False):
        result = super()._ocd_report_problem(reason, note=note)
        self.filtered(lambda p: p.ocd_express and p.ocd_stage == "problem")._ocd_express_notify("problem")
        return result

    def _ocd_return(self, event="returned"):
        """Override of `ocd_live_shop`: a parcel of OCD Express goes back to its sender, against
        their return code; one not picked up yet is cancelled."""
        express = self.filtered("ocd_express")
        super(StockPicking, self - express)._ocd_return(event)
        for parcel in express.sudo():
            if parcel.ocd_stage in ("to_prepare", "ready") and not parcel.ocd_picked_at:
                parcel._ocd_express_cancel(self.env._("Cancelled before the pick-up."))
                continue
            vals = {
                "ocd_stage": "returned",
                "ocd_express_return_state": "to_return",
                "ocd_express_return_code": f"{secrets.randbelow(10 ** 6):06d}",
                "ocd_express_return_attempts": 0,
            }
            if parcel.ocd_cod_state == "collected" and parcel.ocd_cod_method == "cash":
                # The courier gives the cash back to the customer with the parcel
                vals.update({"ocd_cod_state": "to_collect", "ocd_cod_collected_amount": 0.0,
                             "ocd_cod_collected_by_id": False, "ocd_cod_collected_at": False,
                             "ocd_cod_method": False, "ocd_remittance_id": False})
            elif parcel.ocd_cod_state in ("collected", "remitted"):
                parcel._ocd_alert(self.env._(
                    "The parcel %(parcel)s goes back: pay %(amount)s back to %(customer)s.",
                    parcel=parcel.name, amount=parcel.ocd_cod_collected_amount, customer=parcel.partner_id.name),
                    ACTIVITY_REFUND)
            parcel.write(vals)
            parcel.activity_feedback(["ocd_live_shop.mail_activity_type_parcel_problem"])
            parcel.message_post(body=self.env._("Goes back to the sender."))
            parcel._ocd_express_notify("returned")
        express.ocd_express_sender_id._ocd_express_check_returns()

    # === MONEY OF THE SENDER === #

    @api.model
    def _ocd_express_move(self, sender, move_type, kind, lines, parcel=None, ref=None):
        """Post a bill (`in_invoice`: OCD owes the sender) or a credit note (`in_refund`: the
        sender owes OCD) of OCD Express. `lines`: [(product xmlid, label, amount)]."""
        company = (parcel.company_id if parcel else sender.company_id) or self.env.company
        move = self.env["account.move"].sudo().create({
            "move_type": move_type,
            "partner_id": sender.id,
            "company_id": company.id,
            "currency_id": company.currency_id.id,
            "invoice_date": fields.Date.context_today(self),
            "ref": ref or (parcel.name if parcel else False),
            "invoice_origin": parcel.name if parcel else False,
            "ocd_picking_id": parcel.id if parcel else False,
            "ocd_express_kind": kind,
            "invoice_line_ids": [Command.create({
                "product_id": self.env.ref(xmlid).product_variant_id.id,
                "name": label,
                "quantity": 1,
                "price_unit": amount,
                "tax_ids": [Command.clear()],
            }) for xmlid, label, amount in lines if amount],
        })
        move.action_post()
        return move

    def _ocd_express_settle(self):
        """Count the money of the parcel for its sender once it reached OCD (cash counted at the
        cash desk, paid on the phone, or nothing to collect): a bill of the money collected for
        them, a credit note of the delivery they pay and of the collecting. Once per parcel."""
        for parcel in self.sudo():
            if not parcel.ocd_express or parcel.ocd_stage != "delivered":
                continue
            if parcel.ocd_vendor_bill_ids.filtered(lambda m: m.ocd_express_kind in ("collected", "fees")):
                continue
            arrived = parcel.ocd_cod_state == "none" or parcel.ocd_cod_state == "remitted" or (
                parcel.ocd_cod_state == "collected" and parcel.ocd_cod_method == "online")
            if not arrived:
                continue
            company = parcel.company_id
            currency = company.currency_id
            sender = parcel.ocd_express_sender_id
            collected = parcel.ocd_cod_collected_amount if parcel.ocd_cod_state != "none" else 0.0
            # The delivery paid by the customer is the money of OCD: only the goods are the sender's
            goods = currency.round(collected - parcel.ocd_fee_amount) if collected else 0.0
            if currency.compare_amounts(goods, 0.0) > 0:
                self._ocd_express_move(sender, "in_invoice", "collected", [(
                    "ocd_express.product_express_collected",
                    self.env._("Money of %(parcel)s collected for you (%(customer)s)",
                               parcel=parcel.name, customer=parcel.partner_id.name), goods)], parcel=parcel)
            fees = []
            if parcel.ocd_express_fee_by == "sender" and parcel.ocd_express_fee:
                fees.append(("ocd_express.product_express_delivery",
                             self.env._("Delivery of %s", parcel.name), parcel.ocd_express_fee))
            commission = company._ocd_express_cod_fee(goods)
            if commission:
                fees.append(("ocd_express.product_express_collecting",
                             self.env._("Collecting %s at the door", parcel.name), commission))
            if fees:
                self._ocd_express_move(sender, "in_refund", "fees", fees, parcel=parcel)
            elif currency.compare_amounts(goods, 0.0) <= 0:
                # Nothing for the sender, nothing owed: noted as counted
                parcel.message_post(body=self.env._("Nothing to pay to the sender for this parcel."))

    # === CUSTOMERS ERASED === #

    @api.model
    def _cron_ocd_express_erase(self):
        """Erase the name, the number and the address of the customers of OCD Express after the
        months of the settings; the amounts and the dates stay for the accounts."""
        company = self.env.company
        months = company.ocd_express_retention_months
        if not months:
            return
        before = fields.Datetime.now() - timedelta(days=30 * months)
        parcels = self.sudo().search([
            ("ocd_express", "=", True),
            ("ocd_express_anonymized", "=", False),
            ("ocd_stage", "in", ("delivered", "returned", "cancelled")),
            ("write_date", "<", before),
            ("create_date", "<", before),
        ], limit=1000)
        for parcel in parcels:
            if parcel.ocd_express_return_state == "to_return" or parcel.ocd_express_claim_state == "open":
                continue
            parcel.partner_id.write({
                "name": self.env._("Customer erased"), "phone": False, "street": False,
                "delivery_landmark": False, "email": False,
            })
            parcel.write({"ocd_express_anonymized": True, "ocd_express_latitude": 0.0, "ocd_express_longitude": 0.0,
                          "ocd_express_claim_note": False})
        if parcels:
            _logger.info("OCD Express: customers of %s parcels erased", len(parcels))

    # === TEXTS OF THE MESSAGES === #

    def _ocd_express_when_text(self):
        """« this afternoon », « tomorrow morning », « Thursday 26 November in the morning »."""
        self.ensure_one()
        _ = self.env._
        day, part = self.ocd_express_deliver_on, self.ocd_express_deliver_part
        if not day:
            return _("soon")
        today = self.company_id._ocd_local_today()
        if day == today:
            return {"morning": _("this morning"), "afternoon": _("this afternoon"), "evening": _("this evening")}.get(
                part, _("today"))
        if day == today + timedelta(days=1):
            return {"morning": _("tomorrow morning"), "afternoon": _("tomorrow afternoon"),
                    "evening": _("tomorrow evening")}.get(part, _("tomorrow"))
        parts = {"morning": _("in the morning"), "afternoon": _("in the afternoon"), "evening": _("in the evening")}
        return f"{day_text(self.env, day, 'EEEE d MMMM')} {parts.get(part, '')}".strip()

    def _ocd_express_amount_text(self):
        """What the customer pays at the door, for the messages."""
        self.ensure_one()
        if self.ocd_cod_state == "to_collect" and self.ocd_cod_amount:
            return self.env._("%s, in cash or by Mobile Money",
                              self.env["ocd.express.pickup"]._ocd_money(self.ocd_cod_amount))
        return self.env._("nothing, it is already paid")

    def _ocd_express_state_text(self):
        """What happened to the parcel, for the message to the sender."""
        self.ensure_one()
        _ = self.env._
        money = self.env["ocd.express.pickup"]._ocd_money
        if self.ocd_express_claim_state == "open":
            return _("your customer reports a problem, its money waits for the answer of the team")
        if self.ocd_express_return_state == "to_return":
            return _("it comes back to you with the courier")
        if self.ocd_express_return_state == "handed_back":
            return _("given back to you")
        if self.ocd_stage == "delivered":
            if self.ocd_cod_collected_amount:
                return _("delivered, %s collected", money(self.ocd_cod_collected_amount))
            return _("delivered")
        if self.ocd_stage == "problem":
            reasons = dict(self._fields["ocd_problem_reason"]._description_selection(self.env))
            return _("%(reason)s, a second passage is planned", reason=(reasons.get(self.ocd_problem_reason) or "").lower())
        if self.ocd_stage == "cancelled" and self.ocd_express_confirm == "not_for_me":
            return _("your customer says it is not for them, the parcel stays with you")
        if self.ocd_stage == "cancelled" and self.ocd_express_check == "refused":
            return _("refused by the team of OCD Live")
        if self.ocd_express_not_taken and self.ocd_stage == "ready":
            return _("not taken at the pick-up (%s), it leaves with the next passage", self.ocd_express_not_taken)
        return dict(self._fields["ocd_stage"]._description_selection(self.env)).get(self.ocd_stage, "")

    def _ocd_express_recipient_values(self, values):
        """The values of the contact of the customer (extended by ocd_express_whatsapp: their
        consent given through the sender)."""
        return values

    # === NOTIFICATIONS (extended by ocd_express_whatsapp) === #

    def _ocd_express_notify(self, event):
        """Tell the customer or the sender about the parcel: created (the customer), moved,
        problem, delivered, returned, handed_back, cancelled, refused, not_for_me, claim,
        claim_closed."""
