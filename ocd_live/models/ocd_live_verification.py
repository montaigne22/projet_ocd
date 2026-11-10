from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

HISTORY_ROWS = 12


class OcdLiveVerification(models.AbstractModel):
    """What the team checks, on one board as in the validated design (BoVerification): the live
    links sent to the directory, the new vendors (and the new products, added by the shop),
    then what was checked today. Each card is approved or refused with a reason sent to the
    vendor."""

    _name = "ocd.live.verification"
    _description = "OCD Live Checks"

    @api.model
    def get_verification_data(self):
        columns = self._ocd_columns()
        pending = sum(len(column["items"]) for column in columns)
        columns.append({
            "key": "done",
            "label": self.env._("Checked today"),
            "empty": self.env._("Nothing checked yet today."),
            "items": self._ocd_history(),
            "done": True,
        })
        return {
            "banner": self._ocd_banner(),
            "average": self._ocd_average_text(),
            "columns": columns,
            "pending": pending,
            "pager": self.env._("%s to check", pending),
        }

    # === HELPERS === #

    @api.model
    def _ocd_ago(self, value):
        """Return how long ago `value` was, e.g. "just now", "4 min ago", "2 h ago"."""
        if not value:
            return ""
        minutes = int((fields.Datetime.now() - value).total_seconds() // 60)
        if minutes < 1:
            return self.env._("just now")
        if minutes < 60:
            return self.env._("%s min ago", minutes)
        if minutes < 24 * 60:
            return self.env._("%s h ago", minutes // 60)
        return self.env._("%s days ago", minutes // (24 * 60))

    @api.model
    def _ocd_reasons(self, applies_to):
        reasons = self.env["ocd.listing.refuse.reason"].search([("applies_to", "=", applies_to)])
        return [{"id": reason.id, "name": reason.name} for reason in reasons]

    @api.model
    def _ocd_today_start(self):
        return self.env["ocd.live.dashboard"]._ocd_day_bounds()[0]

    # === BANNER === #

    @api.model
    def _ocd_banner(self):
        company = self.env.company
        found = self.env["ocd.directory.window"]._ocd_find(company=company)
        if not found:
            return {"open": False, "text": self.env._("No checking window is set for the directory.")}
        window, start, end = found
        now = fields.Datetime.now()
        hours = f"{company._ocd_to_local(start):%H:%M} – {company._ocd_to_local(end):%H:%M}"
        city = company.ocd_studio_city or "Lomé"
        if start <= now:
            text = self.env._(
                "Window of the directory open: %(window)s, %(hours)s, time of %(city)s. "
                "The lives sent before the opening wait here.",
                window=window.name.lower(),
                hours=hours,
                city=city,
            )
        else:
            text = self.env._(
                "Next window of the directory: %(window)s, %(hours)s, time of %(city)s. "
                "The lives sent before it wait for its opening.",
                window=window.name.lower(),
                hours=hours,
                city=city,
            )
        return {"open": start <= now, "text": text}

    @api.model
    def _ocd_average_text(self):
        listings = self.env["ocd.directory.listing"].search([
            ("company_id", "=", self.env.company.id),
            ("checked_at", ">=", fields.Datetime.now() - timedelta(days=7)),
            ("window_start", "!=", False),
        ], limit=200)
        delays = [
            (listing.checked_at - max(listing.create_date, listing.window_start)).total_seconds() / 60
            for listing in listings
        ]
        delays = [delay for delay in delays if delay >= 0]
        if not delays:
            return ""
        return self.env._("Average checking time: %s min", max(1, round(sum(delays) / len(delays))))

    # === COLUMNS === #

    @api.model
    def _ocd_columns(self):
        """Return the columns of the cards to check. The shop adds the new products."""
        return [
            {
                "key": "link",
                "label": self.env._("Lives sent"),
                "empty": self.env._("No live waiting."),
                "items": self._ocd_link_items(),
            },
            {
                "key": "vendor",
                "label": self.env._("New vendors"),
                "empty": self.env._("No vendor waiting."),
                "items": self._ocd_vendor_items(),
            },
        ]

    @api.model
    def _ocd_link_items(self):
        # The links of a window that just opened are to check, even before the scheduled action
        now = fields.Datetime.now()
        self.env["ocd.directory.listing"].search([
            ("company_id", "=", self.env.company.id),
            ("state", "=", "queued"),
            ("window_start", "<=", now),
            ("window_end", ">", now),
        ]).write({"state": "to_check"})
        listings = self.env["ocd.directory.listing"].search(
            [("company_id", "=", self.env.company.id), ("state", "in", ("to_check", "queued"))],
            order="state desc, create_date",
        )
        reasons = self._ocd_reasons("link")
        company = self.env.company
        items = []
        for listing in listings:
            queued = listing.state == "queued"
            parts = [listing.country_id.name, listing.category_id.name, self.env._("sent %s", self._ocd_ago(listing.create_date))]
            items.append({
                "key": f"link_{listing.id}",
                "kind": "link",
                "id": listing.id,
                "title": listing.title or listing.partner_id.name,
                "sub": " · ".join(part for part in parts if part),
                "detail": (listing.url or "").split("://", 1)[-1],
                "open_url": listing.url,
                "open_label": self.env._("Open the live"),
                "ok_label": self.env._("Show"),
                "reasons": reasons,
                "waiting": self.env._(
                    "Checked at %s, when the window opens.",
                    company._ocd_to_local(listing.window_start).strftime("%H:%M"),
                ) if queued and listing.window_start else "",
            })
        return items

    @api.model
    def _ocd_vendor_items(self):
        vendors = self.env["res.partner"].search(
            [("ocd_is_vendor", "=", True), ("ocd_vendor_state", "=", "to_check")], order="create_date"
        )
        reasons = self._ocd_reasons("vendor")
        company = self.env.company
        items = []
        for vendor in vendors:
            registered = company._ocd_to_local(vendor.create_date).strftime("%H:%M")
            parts = [vendor.country_id.name, vendor.city, vendor.ocd_category_id.name,
                     self.env._("registered at %s", registered)]
            detail = vendor.ocd_business or ""
            if vendor.phone:
                detail = f"{detail} · {vendor.phone}" if detail else vendor.phone
            items.append({
                "key": f"vendor_{vendor.id}",
                "kind": "vendor",
                "id": vendor.id,
                "title": vendor.name,
                "sub": " · ".join(part for part in parts if part),
                "detail": detail,
                "open_label": self.env._("See the record"),
                "open_action": self.env["ocd.live.dashboard"]._ocd_record_action(vendor),
                "ok_label": self.env._("Validate the vendor"),
                "reasons": reasons,
                "choices": self._ocd_vendor_choices(vendor),
            })
        return items

    @api.model
    def _ocd_vendor_choices(self, vendor):
        """Hook: fields chosen when a vendor is validated, as dicts with `name`, `label`,
        `value` and `options` (the shop adds the sale mode)."""
        return []

    # === CHECKED TODAY === #

    @api.model
    def _ocd_history(self):
        """Return what was checked today, the latest first."""
        since = self._ocd_today_start()
        rows = []
        for listing in self.env["ocd.directory.listing"].search(
            [("company_id", "=", self.env.company.id), ("checked_at", ">=", since)]
        ):
            published = listing.state in ("published", "ended")
            rows.append(self._ocd_history_row(
                listing.checked_at,
                listing.title or listing.partner_id.name,
                self.env._("Live shown") if published
                else self.env._("Refused · %s", (listing.refuse_reason_id.name or "").lower()),
                published,
            ))
        for vendor in self.env["res.partner"].search(
            [("ocd_is_vendor", "=", True), ("ocd_vendor_checked_at", ">=", since)]
        ):
            approved = vendor.ocd_vendor_state == "approved"
            rows.append(self._ocd_history_row(
                vendor.ocd_vendor_checked_at,
                vendor.name,
                self.env._("Vendor validated") if approved else self.env._("Vendor refused"),
                approved,
            ))
        rows += self._ocd_history_rows(since)
        rows.sort(key=lambda row: row.pop("sort"), reverse=True)
        return rows[:HISTORY_ROWS]

    @api.model
    def _ocd_history_rows(self, since):
        """Hook: other rows checked today (the shop adds the products)."""
        return []

    @api.model
    def _ocd_history_row(self, moment, title, result, ok):
        return {
            "key": f"done_{title}_{moment}",
            "sort": moment,
            "title": title,
            "result": f"{result} · {self.env.company._ocd_to_local(moment):%H:%M}",
            "ok": ok,
        }

    # === ACTIONS === #

    @api.model
    def ocd_approve(self, kind, record_id, values=None):
        record = self._ocd_record(kind, record_id)
        if kind == "link":
            record.action_publish()
        elif kind == "vendor":
            allowed = {choice["name"] for choice in self._ocd_vendor_choices(record)}
            record.write({key: value for key, value in (values or {}).items() if key in allowed})
            record.action_ocd_approve_vendor()
        return True

    @api.model
    def ocd_refuse(self, kind, record_id, reason_id):
        record = self._ocd_record(kind, record_id)
        reason = self.env["ocd.listing.refuse.reason"].browse(reason_id).exists()
        if not reason:
            raise UserError(self.env._("Choose the reason sent to the vendor."))
        if kind == "link":
            record._ocd_refuse(reason)
        elif kind == "vendor":
            record.action_ocd_refuse_vendor(reason)
        return True

    @api.model
    def _ocd_record(self, kind, record_id):
        models_by_kind = self._ocd_models()
        if kind not in models_by_kind:
            raise UserError(self.env._("Unknown kind of check: %s", kind))
        record = self.env[models_by_kind[kind]].browse(record_id).exists()
        if not record:
            raise UserError(self.env._("This record no longer exists."))
        return record

    @api.model
    def _ocd_models(self):
        return {"link": "ocd.directory.listing", "vendor": "res.partner"}
