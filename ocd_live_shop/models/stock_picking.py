import logging
import secrets
from datetime import timedelta

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import consteq

from odoo.addons.payment import utils as payment_utils

from .res_company import DELIVERY_MODES

_logger = logging.getLogger(__name__)

STAGES = [
    ("to_prepare", "To prepare"),
    ("ready", "Ready"),
    ("picked", "Picked up"),
    ("on_the_way", "On the way"),
    ("delivered", "Delivered"),
    ("problem", "Problem"),
    ("returned", "Returned"),
    ("cancelled", "Cancelled"),
]
OPEN_STAGES = ("to_prepare", "ready", "picked", "on_the_way", "problem")
PROBLEM_REASONS = [
    ("unreachable", "Customer unreachable"),
    ("absent", "Customer absent"),
    ("refused", "Customer refused the parcel"),
    ("address", "Address not found"),
    ("damaged", "Parcel damaged"),
    ("other", "Other"),
]
# Reasons that count as a failed delivery attempt
FAILED_REASONS = {"unreachable", "absent", "refused", "address"}
COD_METHODS = [
    ("cash", "Cash"),
    ("online", "Paid on the phone"),
    ("momo_declared", "Mobile Money declared"),
]
ACTIVITY_PROBLEM = "ocd_live_shop.mail_activity_type_parcel_problem"
ACTIVITY_LATE = "ocd_live_shop.mail_activity_type_parcel_late"
ACTIVITY_REFUND = "ocd_live_shop.mail_activity_type_refund"


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ocd_is_parcel = fields.Boolean(string="OCD Parcel", copy=False, index=True)
    ocd_vendor_id = fields.Many2one(
        comodel_name="res.partner", string="OCD Vendor", copy=False, index="btree_not_null"
    )
    ocd_delivery_mode = fields.Selection(
        selection=DELIVERY_MODES, string="Who Delivers", copy=False, tracking=True
    )
    ocd_courier_id = fields.Many2one(
        comodel_name="res.partner",
        string="Delivered By",
        copy=False,
        tracking=True,
        index="btree_not_null",
    )
    ocd_stage = fields.Selection(
        selection=STAGES, string="Parcel Step", copy=False, tracking=True, index=True
    )
    ocd_ready_at = fields.Datetime(string="Ready At", copy=False)
    ocd_picked_at = fields.Datetime(string="Picked Up At", copy=False)
    ocd_left_at = fields.Datetime(string="Left At", copy=False)
    ocd_delivered_at = fields.Datetime(string="Delivered At", copy=False)
    ocd_delivery_code = fields.Char(
        string="Delivery Code",
        copy=False,
        groups="base.group_system",
        help="Sent to the customer when the parcel leaves. Only the customer sees it.",
    )
    ocd_code_sent_at = fields.Datetime(string="Code Sent At", copy=False)
    ocd_code_attempts = fields.Integer(string="Wrong Codes", copy=False)
    ocd_code_locked = fields.Boolean(string="Locked", copy=False, tracking=True)
    ocd_failed_attempts = fields.Integer(string="Failed Attempts", copy=False)
    ocd_problem_reason = fields.Selection(
        selection=PROBLEM_REASONS, string="Problem", copy=False, tracking=True
    )
    ocd_problem_note = fields.Text(string="Problem Note", copy=False)
    ocd_reminded_at = fields.Datetime(string="Vendor Reminded At", copy=False)
    ocd_escalated_at = fields.Datetime(string="Dispatch Alerted At", copy=False)
    ocd_is_late = fields.Boolean(string="Late", compute="_compute_ocd_is_late")
    ocd_currency_id = fields.Many2one(related="sale_id.currency_id", string="Order Currency")
    ocd_goods_amount = fields.Monetary(
        string="Goods", copy=False, currency_field="ocd_currency_id"
    )
    ocd_fee_amount = fields.Monetary(
        string="Delivery Fee",
        compute="_compute_ocd_fee_amount",
        currency_field="ocd_currency_id",
        help="Share of the delivery fee of the order: the fee goes to the one who delivers.",
    )
    ocd_vendor_share = fields.Monetary(
        string="Share Of The Vendor",
        compute="_compute_ocd_vendor_share",
        currency_field="ocd_currency_id",
    )
    ocd_cod_state = fields.Selection(
        selection=[
            ("none", "Paid online"),
            ("to_collect", "To collect"),
            ("collected", "Collected"),
            ("remitted", "Handed over"),
        ],
        string="Payment At The Door",
        copy=False,
        default="none",
        tracking=True,
    )
    ocd_cod_amount = fields.Monetary(
        string="To Collect",
        compute="_compute_ocd_cod_amount",
        currency_field="ocd_currency_id",
    )
    ocd_cod_collected_amount = fields.Monetary(
        string="Collected", copy=False, currency_field="ocd_currency_id"
    )
    ocd_cod_method = fields.Selection(selection=COD_METHODS, string="Paid With", copy=False)
    ocd_cod_reference = fields.Char(string="Payment Reference", copy=False)
    ocd_cod_collected_by_id = fields.Many2one(
        comodel_name="res.partner", string="Collected By", copy=False, index="btree_not_null"
    )
    ocd_cod_collected_at = fields.Datetime(string="Collected At", copy=False)
    ocd_remittance_id = fields.Many2one(
        comodel_name="ocd.cash.remittance", string="Handed Over In", copy=False, index="btree_not_null"
    )
    ocd_payment_transaction_id = fields.Many2one(
        comodel_name="payment.transaction", string="Mobile Money Request", copy=False
    )
    ocd_forced_by_id = fields.Many2one(comodel_name="res.users", string="Validated Without Code By", copy=False)
    ocd_force_reason = fields.Text(string="Reason Of The Validation Without Code", copy=False)
    ocd_force_photo = fields.Binary(string="Photo Of The Handover", attachment=True, copy=False)
    ocd_vendor_bill_ids = fields.One2many(
        comodel_name="account.move", inverse_name="ocd_picking_id", string="Vendor Bills"
    )
    ocd_customer_phone = fields.Char(related="partner_id.phone", string="Customer Phone")
    ocd_district_id = fields.Many2one(related="partner_id.district_id", string="District")
    ocd_landmark = fields.Char(related="partner_id.delivery_landmark", string="Landmark")

    @api.depends("ocd_stage", "ocd_escalated_at")
    def _compute_ocd_is_late(self):
        for picking in self:
            picking.ocd_is_late = bool(picking.ocd_escalated_at) and picking.ocd_stage in (
                "to_prepare",
                "ready",
            )

    @api.depends("sale_id.order_line.price_total", "sale_id.picking_ids.state")
    def _compute_ocd_fee_amount(self):
        for picking in self:
            order = picking.sale_id
            if not picking.ocd_is_parcel or not order:
                picking.ocd_fee_amount = 0.0
                continue
            parcels = order.picking_ids.filtered(
                lambda p: p.ocd_is_parcel and p.ocd_stage != "cancelled" and p.state != "cancel"
            )
            count = len(parcels) or 1
            picking.ocd_fee_amount = order.currency_id.round(order._ocd_delivery_fee() / count)

    @api.depends("ocd_goods_amount", "ocd_fee_amount", "ocd_delivery_mode", "ocd_courier_id")
    def _compute_ocd_vendor_share(self):
        for picking in self:
            share = 0.0
            for move in picking.move_ids.filtered(lambda m: m.sale_line_id and m.state != "cancel"):
                line = move.sale_line_id
                if line.ocd_vendor_id and line.product_uom_qty:
                    share += line.ocd_vendor_share * move.product_uom_qty / line.product_uom_qty
            if picking._ocd_vendor_delivers():
                share += picking.ocd_fee_amount
            picking.ocd_vendor_share = picking.ocd_currency_id.round(share) if picking.ocd_currency_id else share

    @api.depends("ocd_goods_amount", "ocd_fee_amount", "ocd_cod_state", "ocd_cod_collected_amount")
    def _compute_ocd_cod_amount(self):
        for picking in self:
            if picking.ocd_cod_state == "to_collect":
                picking.ocd_cod_amount = picking.ocd_goods_amount + picking.ocd_fee_amount
            else:
                picking.ocd_cod_amount = picking.ocd_cod_collected_amount

    def action_cancel(self):
        result = super().action_cancel()
        self.filtered(lambda p: p.ocd_is_parcel and p.ocd_stage in OPEN_STAGES).write({"ocd_stage": "cancelled"})
        return result

    # === CREATION OF THE PARCELS === #

    def _ocd_init_parcels(self):
        """Turn the deliveries of shop orders into parcels: who delivers, courier, amounts."""
        Partner = self.env["res.partner"]
        for picking in self:
            if picking.ocd_is_parcel or picking.picking_type_code != "outgoing" or not picking.sale_id:
                continue
            vendor = picking.ocd_vendor_id
            mode = (vendor.ocd_delivery_mode if vendor else "stock") or picking.company_id.ocd_default_delivery_mode
            district = picking.partner_id.district_id
            note = False
            if (
                mode == "vendor"
                and vendor.ocd_zone_ids
                and district
                and district not in vendor.ocd_zone_ids
                and vendor.ocd_zone_fallback
            ):
                mode = "pickup"
                note = self.env._(
                    "%(district)s is outside the zones of %(vendor)s: an OCD courier delivers.",
                    district=district.name,
                    vendor=vendor.name,
                )
            courier = vendor if mode == "vendor" else Partner._ocd_find_courier(district)
            picking.write({
                "ocd_is_parcel": True,
                "ocd_delivery_mode": mode,
                "ocd_courier_id": courier.id,
                "ocd_stage": "to_prepare",
                "ocd_goods_amount": picking._ocd_compute_goods_amount(),
                "ocd_cod_state": "none" if picking.sale_id._ocd_is_paid_online() else "to_collect",
            })
            if note:
                picking.message_post(body=note)
            picking._ocd_notify_new_parcel()

    def _ocd_compute_goods_amount(self):
        self.ensure_one()
        total = 0.0
        for move in self.move_ids.filtered(lambda m: m.sale_line_id and m.state != "cancel"):
            line = move.sale_line_id
            if line.product_uom_qty:
                total += line.price_total * move.product_uom_qty / line.product_uom_qty
        return self.sale_id.currency_id.round(total)

    def _ocd_vendor_delivers(self):
        self.ensure_one()
        return bool(self.ocd_vendor_id) and self.ocd_courier_id == self.ocd_vendor_id

    # === STEPS === #

    def _ocd_check_stage(self, allowed):
        stages = dict(self._fields["ocd_stage"]._description_selection(self.env))
        for picking in self:
            if not picking.ocd_is_parcel:
                raise UserError(self.env._("%s is not a parcel of the shop.", picking.name))
            if picking.ocd_stage not in allowed:
                raise UserError(
                    self.env._(
                        "This step is not possible: the parcel %(parcel)s is %(stage)s.",
                        parcel=picking.name,
                        stage=stages.get(picking.ocd_stage, ""),
                    )
                )

    def action_ocd_ready(self):
        self._ocd_check_stage(("to_prepare",))
        self.write({"ocd_stage": "ready", "ocd_ready_at": fields.Datetime.now()})
        return True

    def action_ocd_pick_up(self):
        self._ocd_check_stage(("to_prepare", "ready"))
        if self.filtered(lambda p: p.ocd_delivery_mode == "vendor"):
            raise UserError(self.env._("The vendor delivers this parcel: nobody picks it up."))
        now = fields.Datetime.now()
        for picking in self:
            picking.write({
                "ocd_stage": "picked",
                "ocd_picked_at": now,
                "ocd_ready_at": picking.ocd_ready_at or now,
            })
        return True

    def action_ocd_leave(self):
        """The parcel leaves: the customer receives the code to give at the handover. The code
        stays the same for a new attempt."""
        self._ocd_check_stage(("ready", "picked"))
        now = fields.Datetime.now()
        for picking in self:
            if not picking.ocd_courier_id:
                raise UserError(self.env._("Choose who delivers the parcel %s first.", picking.name))
            # sudo: the code is restricted to administrators, it is only generated here
            picking_sudo = picking.sudo()
            vals = {"ocd_stage": "on_the_way", "ocd_left_at": now, "ocd_code_sent_at": now}
            if not picking_sudo.ocd_delivery_code:
                vals.update({"ocd_delivery_code": f"{secrets.randbelow(10000):04d}", "ocd_code_attempts": 0})
            picking_sudo.write(vals)
            picking._ocd_send_code()
        return True

    def action_ocd_resend_code(self):
        self._ocd_check_stage(("on_the_way",))
        for picking in self:
            picking._ocd_send_code()
        return True

    def _ocd_check_code(self, code):
        """Check the code given by the customer. Return a tuple (delivered, attempts left)."""
        self.ensure_one()
        self._ocd_check_stage(("on_the_way",))
        if self.ocd_code_locked:
            raise UserError(self.env._("This parcel is locked after too many wrong codes. Call the team."))
        expected = self.sudo().ocd_delivery_code or ""
        code = (code or "").strip()
        if expected and code and consteq(code, expected):
            self._ocd_deliver()
            return True, 0
        max_attempts = self.company_id.ocd_code_max_attempts or 3
        attempts = self.ocd_code_attempts + 1
        locked = attempts >= max_attempts
        self.sudo().write({"ocd_code_attempts": attempts, "ocd_code_locked": locked})
        if locked:
            self._ocd_alert(
                self.env._("Parcel %(parcel)s locked after %(count)s wrong codes.", parcel=self.name, count=attempts),
                ACTIVITY_PROBLEM,
            )
        return False, max(max_attempts - attempts, 0)

    def _ocd_force_deliver(self, reason, photo=False):
        """Validate a parcel without the code of the customer: managers only, with a reason."""
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only a manager can validate a parcel without the code."))
        if not (reason or "").strip():
            raise UserError(self.env._("Write why the parcel is validated without the code."))
        self._ocd_check_stage(("ready", "picked", "on_the_way", "problem"))
        self.sudo().write({
            "ocd_forced_by_id": self.env.uid,
            "ocd_force_reason": reason,
            "ocd_force_photo": photo or False,
        })
        for picking in self:
            picking.message_post(
                body=self.env._(
                    "Delivered without the code, validated by %(user)s: %(reason)s",
                    user=self.env.user.name,
                    reason=reason,
                )
            )
        self._ocd_deliver()
        return True

    def _ocd_deliver(self):
        now = fields.Datetime.now()
        for picking in self:
            picking._ocd_validate_transfer()
            picking.sudo().write({"ocd_stage": "delivered", "ocd_delivered_at": now, "ocd_problem_reason": False})
            picking._ocd_create_vendor_bills()
            picking._ocd_notify_customer("delivered")

    def _ocd_validate_transfer(self):
        """Validate the stock transfer of the parcel, without backorder."""
        self.ensure_one()
        # sudo: the vendors and the couriers validate their parcels through their apps
        picking = self.sudo()
        if picking.state == "done":
            return
        if picking.state == "draft":
            picking.action_confirm()
        if picking.state != "assigned":
            picking.action_assign()
        for move in picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
            if move.uom_id.compare(move.quantity, move.product_uom_qty) < 0:
                move.quantity = move.product_uom_qty
            move.picked = True
        picking.with_context(
            skip_backorder=True, picking_ids_not_to_backorder=picking.ids, skip_sms=True
        ).button_validate()

    def _ocd_report_problem(self, reason, note=False):
        """Note a delivery problem. Too many failed attempts send the parcel back."""
        self._ocd_check_stage(("ready", "picked", "on_the_way"))
        for picking in self:
            failed = picking.ocd_failed_attempts + (1 if reason in FAILED_REASONS else 0)
            picking.write({
                "ocd_stage": "problem",
                "ocd_problem_reason": reason,
                "ocd_problem_note": note or False,
                "ocd_failed_attempts": failed,
            })
            picking._ocd_notify_customer("failed")
            if failed >= (picking.company_id.ocd_max_failed_attempts or 2):
                picking._ocd_return()
            else:
                reasons = dict(self._fields["ocd_problem_reason"]._description_selection(self.env))
                picking._ocd_alert(
                    self.env._("Problem with the parcel %(parcel)s: %(reason)s", parcel=picking.name, reason=reasons[reason]),
                    ACTIVITY_PROBLEM,
                )
        return True

    def action_ocd_retry(self):
        """Try again: the parcel goes back to its courier, with the same code."""
        self._ocd_check_stage(("problem",))
        for picking in self:
            stage = "picked" if picking.ocd_picked_at else "ready"
            picking.write({"ocd_stage": stage, "ocd_problem_reason": False, "ocd_problem_note": False})
            picking.activity_feedback([ACTIVITY_PROBLEM])
        return True

    def action_ocd_return(self):
        self._ocd_check_stage(("problem", "to_prepare", "ready", "picked"))
        self._ocd_return()
        return True

    def _ocd_return(self):
        for picking in self:
            picking.write({"ocd_stage": "returned"})
            if picking.state not in ("done", "cancel"):
                picking.sudo().action_cancel()
            picking.activity_feedback([ACTIVITY_PROBLEM])
            if picking.sale_id and picking.sale_id._ocd_is_paid_online():
                picking._ocd_alert(
                    self.env._(
                        "The parcel %(parcel)s goes back: refund %(amount)s to the customer.",
                        parcel=picking.name,
                        amount=picking.ocd_goods_amount + picking.ocd_fee_amount,
                    ),
                    ACTIVITY_REFUND,
                )
            picking._ocd_notify_customer("returned")

    def _ocd_assign_courier(self, courier):
        self._ocd_check_stage(OPEN_STAGES)
        for picking in self:
            vals = {"ocd_courier_id": courier.id}
            if courier and courier == picking.ocd_vendor_id:
                vals["ocd_delivery_mode"] = "vendor"
            elif picking.ocd_delivery_mode == "vendor":
                vals["ocd_delivery_mode"] = "pickup"
            picking.write(vals)
        return True

    def action_ocd_switch_to_ocd(self):
        """Give the parcel to an OCD courier (vendor late or unavailable)."""
        self._ocd_check_stage(("to_prepare", "ready", "problem"))
        Partner = self.env["res.partner"]
        for picking in self:
            courier = Partner._ocd_find_courier(picking.ocd_district_id)
            picking.write({"ocd_delivery_mode": "pickup", "ocd_courier_id": courier.id})
            picking.message_post(
                body=self.env._("The parcel goes to an OCD courier: %s.", courier.name or self.env._("to choose"))
            )
            picking.activity_feedback([ACTIVITY_LATE])
        return True

    def action_ocd_open_problem_wizard(self):
        return self._ocd_wizard_action("ocd.parcel.problem", self.env._("Delivery problem"))

    def action_ocd_open_force_wizard(self):
        return self._ocd_wizard_action("ocd.parcel.force", self.env._("Validate without the code"))

    def action_ocd_open_code_wizard(self):
        return self._ocd_wizard_action("ocd.parcel.code", self.env._("Code of the customer"))

    def _ocd_wizard_action(self, model, name):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": model,
            "view_mode": "form",
            "target": "new",
            "context": {"default_picking_id": self.id},
        }

    # === PAYMENT AT THE DOOR === #

    def _ocd_allowed_cod_methods(self, collector):
        """Return the payment methods the `collector` may record at the door."""
        self.ensure_one()
        company = self.company_id
        methods = []
        if collector and collector == self.ocd_vendor_id and not self.ocd_vendor_id.ocd_vendor_collects:
            return methods
        if company.ocd_cod_cash:
            methods.append("cash")
        if company.ocd_cod_online:
            methods.append("online")
        if company.ocd_cod_momo_declared:
            methods.append("momo_declared")
        return methods

    def _ocd_collect(self, method, collector, reference=False):
        """Record the money collected at the door by `collector`."""
        self.ensure_one()
        if self.ocd_cod_state != "to_collect":
            raise UserError(self.env._("There is nothing to collect for the parcel %s.", self.name))
        # A payment on the phone is confirmed by the provider, not by the one at the door
        if method != "online" and method not in self._ocd_allowed_cod_methods(collector):
            raise UserError(self.env._("This payment method is not allowed for this parcel."))
        if method == "momo_declared" and not (reference or "").strip():
            raise UserError(self.env._("Type the reference of the Mobile Money payment."))
        amount = self.ocd_cod_amount
        self.sudo().write({
            "ocd_cod_state": "collected",
            "ocd_cod_method": method,
            "ocd_cod_reference": reference or False,
            "ocd_cod_collected_by_id": collector.id,
            "ocd_cod_collected_at": fields.Datetime.now(),
            "ocd_cod_collected_amount": amount,
        })
        if self.ocd_stage == "delivered":
            self._ocd_create_collection_refund()
        return True

    def _ocd_payment_url(self):
        """Return the page where the customer pays the parcel on the phone, with the payment
        methods Odoo offers for the country of the customer. Opened from the QR code shown by
        the courier."""
        self.ensure_one()
        if not self.company_id.ocd_cod_online:
            raise UserError(self.env._("The payment on the phone of the customer is not enabled."))
        if self.ocd_cod_state != "to_collect":
            raise UserError(self.env._("There is nothing to collect for the parcel %s.", self.name))
        token = payment_utils.generate_access_token(self.id, self.ocd_cod_amount, env=self.env)
        return f"{self.get_base_url()}/ocd/colis/{self.id}/payer?access_token={token}"

    # === MONEY OF THE VENDOR === #

    def _ocd_bill_product(self, xmlid):
        return self.env.ref(xmlid).product_variant_id

    def _ocd_create_vendor_bills(self):
        """Create the vendor bill of the share of the vendor (and of the delivery fee when the
        vendor delivered), then the credit note of the money the vendor collected."""
        AccountMove = self.env["account.move"].sudo()
        today = fields.Date.context_today(self)
        for picking in self:
            vendor = picking.ocd_vendor_id
            if not vendor or picking.ocd_vendor_bill_ids.filtered(lambda m: m.move_type == "in_invoice"):
                continue
            share = picking.ocd_vendor_share - (picking.ocd_fee_amount if picking._ocd_vendor_delivers() else 0.0)
            lines = [Command.create({
                "product_id": picking._ocd_bill_product("ocd_live_shop.product_vendor_share").id,
                "name": self.env._("Share of the sales of %(parcel)s (%(order)s)", parcel=picking.name, order=picking.sale_id.name),
                "quantity": 1,
                "price_unit": share,
                "tax_ids": [Command.clear()],
            })]
            if picking._ocd_vendor_delivers() and picking.ocd_fee_amount:
                lines.append(Command.create({
                    "product_id": picking._ocd_bill_product("ocd_live_shop.product_vendor_delivery").id,
                    "name": self.env._("Delivery of %s", picking.name),
                    "quantity": 1,
                    "price_unit": picking.ocd_fee_amount,
                    "tax_ids": [Command.clear()],
                }))
            bill = AccountMove.create({
                "move_type": "in_invoice",
                "partner_id": vendor.id,
                "company_id": picking.company_id.id,
                "currency_id": picking.ocd_currency_id.id,
                "invoice_date": today,
                "ref": picking.name,
                "invoice_origin": picking.sale_id.name,
                "ocd_picking_id": picking.id,
                "invoice_line_ids": lines,
            })
            bill.action_post()
            picking._ocd_create_collection_refund()

    def _ocd_create_collection_refund(self):
        """The vendor kept the money of the customer: it is withheld from the next payout."""
        AccountMove = self.env["account.move"].sudo()
        for picking in self:
            vendor = picking.ocd_vendor_id
            if (
                not vendor
                or picking.ocd_cod_state not in ("collected", "remitted")
                or picking.ocd_cod_collected_by_id != vendor
                or picking.ocd_vendor_bill_ids.filtered(lambda m: m.move_type == "in_refund")
            ):
                continue
            refund = AccountMove.create({
                "move_type": "in_refund",
                "partner_id": vendor.id,
                "company_id": picking.company_id.id,
                "currency_id": picking.ocd_currency_id.id,
                "invoice_date": fields.Date.context_today(self),
                "ref": picking.name,
                "invoice_origin": picking.sale_id.name,
                "ocd_picking_id": picking.id,
                "invoice_line_ids": [Command.create({
                    "product_id": picking._ocd_bill_product("ocd_live_shop.product_vendor_collected").id,
                    "name": self.env._("Money of %s collected by the vendor", picking.name),
                    "quantity": 1,
                    "price_unit": picking.ocd_cod_collected_amount,
                    "tax_ids": [Command.clear()],
                })],
            })
            refund.action_post()

    # === NOTIFICATIONS (extended by ocd_live_whatsapp) === #

    def _ocd_notify_new_parcel(self):
        """Tell the one who prepares the parcel that there is a new parcel."""

    def _ocd_send_code(self):
        """Send the delivery code to the customer. The customer also sees it on the order
        page of the customer portal."""

    def _ocd_remind_vendor(self):
        """Remind the vendor of a parcel not prepared in time."""
        self.ensure_one()
        self.message_post(body=self.env._("The vendor was reminded: the parcel is not ready yet."))

    def _ocd_notify_customer(self, event):
        """Tell the customer about the parcel (failed attempt, delivered, returned)."""

    def _ocd_alert(self, body, activity_xmlid=False):
        """Alert the team: message in the deliveries channel and activity on the parcel."""
        self.ensure_one()
        channel = self.company_id.ocd_deliveries_channel_id
        if channel:
            # sudo: alerts are posted by the system, also from the apps of the couriers
            channel.sudo().message_post(body=body, message_type="comment", subtype_xmlid="mail.mt_comment")
        if activity_xmlid:
            user = self.company_id.ocd_live_responsible_id or self.env.ref("base.user_admin", raise_if_not_found=False)
            self.sudo().activity_schedule(activity_xmlid, note=body, user_id=user.id if user else self.env.uid)

    # === CRONS === #

    @api.model
    def _cron_ocd_escalate(self):
        """Remind the vendors whose parcel is not ready in time, then alert the dispatch."""
        now = fields.Datetime.now()
        parcels = self.search([
            ("ocd_is_parcel", "=", True),
            ("ocd_stage", "=", "to_prepare"),
            ("ocd_delivery_mode", "in", ("vendor", "pickup")),
            ("ocd_escalated_at", "=", False),
        ])
        for picking in parcels:
            company = picking.company_id
            if not picking.ocd_reminded_at:
                prep_hours = picking.ocd_vendor_id._ocd_prep_hours() if picking.ocd_vendor_id else company.ocd_prep_hours
                if picking.create_date + timedelta(hours=prep_hours) <= now:
                    picking.ocd_reminded_at = now
                    picking._ocd_remind_vendor()
            elif picking.ocd_reminded_at + timedelta(hours=company.ocd_escalation_hours) <= now:
                picking.ocd_escalated_at = now
                picking._ocd_alert(
                    self.env._(
                        "%(vendor)s has not prepared the parcel %(parcel)s yet: give it to an OCD courier?",
                        vendor=picking.ocd_vendor_id.name or "-",
                        parcel=picking.name,
                    ),
                    ACTIVITY_LATE,
                )
