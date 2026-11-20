# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import datetime
import re

from odoo import _, api, models

from odoo.addons.purchase_rfq_round_sheet.wizards.purchase_rfq_round_import import (
    _normalize,
    _to_float,
)

YES = {"s", "sim", "y", "yes", "x", "ok", "1", "true", "verdadeiro"}
NO = {"n", "nao", "no", "0", "false", "falso"}


class PurchaseRfqRoundImport(models.TransientModel):
    _inherit = "purchase.rfq.round.import"

    @api.model
    def _get_import_columns(self):
        columns = super()._get_import_columns()
        columns += [
            {
                "key": "payment_term",
                "label": _("Payment Terms"),
                "synonyms": [
                    "condicao de pagamento",
                    "condicoes de pagamento",
                    "payment terms",
                    "pagamento",
                    "cond pgto",
                ],
                "apply": self._apply_payment_term,
            },
            {
                "key": "validity",
                "label": _("Valid Until"),
                "synonyms": ["validade", "valid until", "validity"],
                "apply": self._apply_validity,
            },
            {
                "key": "min_qty",
                "label": _("Minimum Qty"),
                "synonyms": [
                    "lote minimo",
                    "quantidade minima",
                    "minimum qty",
                    "moq",
                    "lote min",
                    "qtd min",
                    "qtde min",
                    "pedido min",
                ],
                "apply": self._apply_min_qty,
            },
            {
                "key": "spec",
                "label": _("Meets Specification"),
                "synonyms": ["atende especificacao", "especificacao", "meets spec"],
                "apply": self._apply_spec,
            },
        ]
        return columns

    @api.model
    def _apply_payment_term(self, po_line, value, vals):
        """Casa pelo nome da condição; número puro vira "N dias"."""
        terms = self.env["account.payment.term"].with_company(
            po_line.order_id.company_id
        )
        text = str(value).strip()
        term = terms.search([("name", "=ilike", text)], limit=1)
        if not term:
            norm = _normalize(text)
            term = next(
                (t for t in terms.search([]) if _normalize(t.name) == norm), terms
            )
        if not term and _normalize(text) in ("a vista", "avista", "imediato"):
            term = next(
                (
                    t
                    for t in terms.search([])
                    if len(t.line_ids) == 1 and not t.line_ids.nb_days
                ),
                terms,
            )
        if not term:
            digits = re.findall(r"\d+", text)
            if len(digits) == 1:
                days = int(digits[0])
                term = next(
                    (
                        t
                        for t in terms.search([])
                        if len(t.line_ids) == 1 and t.line_ids.nb_days == days
                    ),
                    terms,
                )
        if term:
            vals["rfq_payment_term_id"] = term.id

    @api.model
    def _apply_validity(self, po_line, value, vals):
        if isinstance(value, datetime.datetime):
            vals["rfq_validity_date"] = value.date()
        elif isinstance(value, datetime.date):
            vals["rfq_validity_date"] = value
        else:
            text = str(value).strip()
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
                try:
                    vals["rfq_validity_date"] = datetime.datetime.strptime(
                        text, fmt
                    ).date()
                    return
                except ValueError:
                    continue

    @api.model
    def _apply_min_qty(self, po_line, value, vals):
        qty = _to_float(value)
        if qty is not None and qty >= 0.0:
            vals["rfq_min_qty"] = qty

    @api.model
    def _apply_spec(self, po_line, value, vals):
        norm = _normalize(value)
        if norm in YES:
            vals["rfq_spec_approved"] = True
        elif norm in NO:
            vals["rfq_spec_approved"] = False

    def action_import(self):
        res = super().action_import()
        self.round_id.line_ids._rfq_compute_scores()
        return res

    def _prepare_response(self, po_line, raw, vals):
        res = super()._prepare_response(po_line, raw, vals)
        res.update(
            {
                "payment_term_id": vals.get("rfq_payment_term_id", False),
                "validity_date": vals.get("rfq_validity_date", False),
                "min_qty": vals.get("rfq_min_qty", 0.0),
                "spec_approved": vals.get("rfq_spec_approved", False),
            }
        )
        return res
