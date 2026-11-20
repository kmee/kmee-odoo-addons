# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class PurchaseRfqRound(models.Model):
    _inherit = "purchase.rfq.round"

    price_basis = fields.Selection(
        [
            ("subtotal", "Subtotal (without taxes)"),
            ("total", "Total (with taxes)"),
            ("present_value", "Present value of total"),
        ],
        default="present_value",
        required=True,
        help="Base do preço na pontuação. O valor presente traz o total com "
        "impostos para hoje pela condição de pagamento respondida, à taxa "
        "mensal da rodada: prazo maior pesa a favor do fornecedor.",
    )
    pv_monthly_rate = fields.Float(
        string="Monthly Rate (%)",
        default=1.0,
        digits=(16, 4),
        help="Taxa mensal usada para trazer os pagamentos a valor presente.",
    )
    weight_price = fields.Float(string="Price Weight", default=70.0)
    weight_delay = fields.Float(string="Lead Time Weight", default=30.0)
    require_approved = fields.Boolean(
        string="Approved Vendors Only",
        help="Só pontua respostas de fornecedor homologado para o produto e "
        "com especificação atendida.",
    )

    def action_compute_scores(self):
        self.line_ids._rfq_compute_scores()
        return True

    def action_award_best_score(self):
        self._check_can_award()
        self.line_ids._rfq_compute_scores()
        for line in self.line_ids:
            line._award(line._get_best_quote("score"))
        return True

    def _get_sheet_columns(self):
        columns = super()._get_sheet_columns()
        notes = columns.pop()
        columns += [
            {
                "key": "payment_term",
                "label": _("Payment Terms"),
                "width": 18,
                "input": True,
                "value": lambda pol: pol.rfq_payment_term_id.name or None,
            },
            {
                "key": "validity",
                "label": _("Valid Until"),
                "width": 12,
                "input": True,
                "value": lambda pol: None,
            },
            {
                "key": "min_qty",
                "label": _("Minimum Qty"),
                "width": 10,
                "input": True,
                "value": lambda pol: None,
            },
            {
                "key": "spec",
                "label": _("Meets Specification (Y/N)"),
                "width": 12,
                "input": True,
                "value": lambda pol: None,
            },
            notes,
        ]
        return columns
