from odoo import api, models
from odoo.tools.misc import format_amount

OPEN_STAGES = ("to_prepare", "ready", "picked", "on_the_way", "problem")


class OcdWhatsappInbox(models.AbstractModel):
    """The shop in the WhatsApp conversations: the last order of a customer and its parcels, the
    parcels a vendor has to prepare, the couriers, the cash to hand over, and the templates of
    the orders and the parcels. The delivery codes stay hidden from the team."""

    _inherit = "ocd.whatsapp.inbox"

    @api.model
    def _ocd_secret_templates(self):
        return super()._ocd_secret_templates() | {"ocd_colis_en_route"}

    @api.model
    def _ocd_partner_role(self, partner):
        if partner.ocd_is_courier and not partner.ocd_is_vendor:
            role = self.env._("Courier")
            if partner.country_id and partner.country_id != self.env.company.country_id:
                role = f"{role} · {partner.country_id.name}"
            return role
        if not partner.ocd_is_vendor and self._ocd_last_order(partner):
            role = self.env._("Customer")
            if partner.country_id and partner.country_id != self.env.company.country_id:
                role = f"{role} · {partner.country_id.name}"
            return role
        return super()._ocd_partner_role(partner)

    @api.model
    def _ocd_partner_place(self, partner):
        if partner.city and partner.district_id:
            return f"{partner.city} · {partner.district_id.name}"
        return super()._ocd_partner_place(partner)

    @api.model
    def _ocd_last_order(self, partner):
        return self.env["sale.order"].sudo().search([
            ("partner_id", "=", partner.id),
            ("state", "in", ("sale", "sent", "draft")),
            ("picking_ids.ocd_is_parcel", "=", True),
        ], order="date_order desc, id desc", limit=1)

    def _ocd_parcel_line(self, parcel):
        _ = self.env._
        stages = dict(parcel._fields["ocd_stage"]._description_selection(self.env))
        text = stages.get(parcel.ocd_stage, "")
        who = parcel.ocd_courier_id.name or (parcel.ocd_vendor_id.name if parcel.ocd_delivery_mode == "vendor" else "")
        if who and parcel.ocd_stage in OPEN_STAGES:
            text = f"{text} · {who}"
        return text

    def _ocd_panel_sections(self, partner):
        sections = super()._ocd_panel_sections(partner)
        _ = self.env._
        order = self._ocd_last_order(partner)
        if order:
            parcels = order.picking_ids.filtered("ocd_is_parcel").sorted("id")
            paid = order.amount_total - sum(parcels.mapped("ocd_cod_amount"))
            payment = _("paid") if paid >= order.amount_total - 0.5 else _("to pay at the door")
            rows = [{"key": _("Total"), "value": f"{format_amount(self.env, order.amount_total, order.currency_id)} · {payment}"}]
            for index, parcel in enumerate(parcels, 1):
                key = _("Parcel %s", index) if len(parcels) > 1 else _("Parcel")
                rows.append({"key": key, "value": self._ocd_parcel_line(parcel)})
            links = [{"label": _("Open the order"), "action": self._ocd_form(order)}]
            links += [
                {"label": _("Open the parcel %s", parcel.name), "action": self._ocd_form(parcel)}
                for parcel in parcels.filtered(lambda p: p.ocd_stage in OPEN_STAGES)[:2]
            ]
            sections.insert(0, {"title": _("Order %s", order.name), "rows": rows, "links": links})
        if partner.ocd_is_vendor:
            parcels = self.env["stock.picking"].sudo().search([
                ("ocd_is_parcel", "=", True), ("ocd_vendor_id", "=", partner.id), ("ocd_stage", "in", OPEN_STAGES),
            ], order="create_date")
            if parcels:
                late = parcels.filtered("ocd_is_late")
                modes = dict(partner._fields["ocd_delivery_mode"]._description_selection(self.env))
                rows = [
                    {"key": _("Delivery"), "value": modes.get(partner.ocd_delivery_mode, "")},
                    {"key": _("Parcels"), "value": _("%(count)s in progress, %(late)s late", count=len(parcels), late=len(late))},
                ]
                rows += [{"key": parcel.name, "value": self._ocd_parcel_line(parcel)} for parcel in parcels[:3]]
                sections.insert(0, {
                    "title": _("Parcels of the vendor"),
                    "rows": rows,
                    "links": [{"label": _("See at the dispatch"), "action": "ocd_live_shop.ocd_live_dispatch_action"}],
                })
        return sections

    def _ocd_template_records(self, partner):
        records = super()._ocd_template_records(partner)
        order = self._ocd_last_order(partner)
        if order:
            records += order.picking_ids.filtered(lambda p: p.ocd_is_parcel and p.ocd_stage in OPEN_STAGES)
            records.append(order)
        return records

    @api.model
    def _ocd_team_channels(self):
        rows = super()._ocd_team_channels()
        company = self.env.company
        for channel in company.ocd_deliveries_channel_id:
            late = len(self.env["stock.picking"].sudo().search(
                [("ocd_is_parcel", "=", True), ("ocd_stage", "in", OPEN_STAGES)]
            ).filtered("ocd_is_late"))
            if late:
                text = self.env._("1 parcel late") if late == 1 else self.env._("%s parcels late", late)
                rows.append(self._ocd_team_channel_row(channel, text=text, tone="red"))
            else:
                rows.append(self._ocd_team_channel_row(channel))
        couriers = self.env["res.partner"].sudo().search([("ocd_is_courier", "=", True)])
        cash = sum(couriers.mapped("ocd_cash_on_hand"))
        if cash:
            rows.append({
                "id": False,
                "name": self.env._("Cash of the couriers"),
                "text": self.env._("%s to hand over", format_amount(self.env, cash, company.currency_id)),
                "time": "",
                "tone": "",
                "action": "ocd_live_shop.ocd_live_couriers_action",
            })
        return rows
