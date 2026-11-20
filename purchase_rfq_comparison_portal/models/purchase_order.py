# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models

from odoo.addons.purchase_rfq_round_portal.models.purchase_order import _parse_float


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _rfq_portal_payment_terms(self):
        return (
            self.env["account.payment.term"]
            .sudo()
            .search([("company_id", "in", [False, self.company_id.id])])
        )

    def _rfq_portal_line_fields(self):
        line_fields = super()._rfq_portal_line_fields()
        terms = self._rfq_portal_payment_terms()
        notes = line_fields.pop()
        line_fields += [
            {
                "key": "payment_term",
                "label": _("Payment Terms"),
                "type": "selection",
                "options": [(term.id, term.name) for term in terms],
                "required": False,
                "get": lambda pol: pol.rfq_payment_term_id.id or "",
                "apply": self._rfq_portal_apply_payment_term,
            },
            {
                "key": "validity",
                "label": _("Valid Until"),
                "type": "date",
                "required": False,
                "get": lambda pol: pol.rfq_validity_date or "",
                "apply": self._rfq_portal_apply_validity,
            },
            {
                "key": "min_qty",
                "label": _("Minimum Qty"),
                "type": "float",
                "required": False,
                "get": lambda pol: self._rfq_portal_format_float(
                    pol.rfq_min_qty, "Product Unit of Measure"
                ),
                "apply": self._rfq_portal_apply_min_qty,
            },
            {
                "key": "spec",
                "label": _("Meets Specification"),
                "type": "bool",
                "required": False,
                "get": lambda pol: pol.rfq_spec_approved,
                "apply": lambda pol, raw, vals: vals.update(
                    rfq_spec_approved=bool(raw)
                ),
            },
            notes,
        ]
        return line_fields

    def _rfq_portal_apply_payment_term(self, pol, raw, vals):
        if not raw:
            return
        terms = self._rfq_portal_payment_terms()
        try:
            term = terms.filtered(lambda t: t.id == int(raw))
        except ValueError as err:
            raise ValueError(_("Invalid payment terms.")) from err
        if not term:
            raise ValueError(_("Invalid payment terms."))
        vals["rfq_payment_term_id"] = term.id

    def _rfq_portal_apply_validity(self, pol, raw, vals):
        if not raw:
            return
        try:
            date = fields.Date.to_date(raw)
        except ValueError as err:
            raise ValueError(_("Invalid date.")) from err
        if date < fields.Date.context_today(self):
            raise ValueError(_("The validity cannot be in the past."))
        vals["rfq_validity_date"] = date

    def _rfq_portal_apply_min_qty(self, pol, raw, vals):
        try:
            qty = _parse_float(raw, self._rfq_portal_decimal_point())
        except ValueError as err:
            raise ValueError(_("Invalid quantity.")) from err
        if qty is not None:
            if qty < 0:
                raise ValueError(_("The quantity cannot be negative."))
            vals["rfq_min_qty"] = qty

    def _rfq_portal_after_submit(self, count):
        res = super()._rfq_portal_after_submit(count)
        self.rfq_round_id.line_ids._rfq_compute_scores()
        return res
