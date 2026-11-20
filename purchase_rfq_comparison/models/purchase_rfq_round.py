# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


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

    def _award_lines(self, criterion, only_unawarded=False):
        if criterion == "score":
            self.line_ids._rfq_compute_scores()
        return super()._award_lines(criterion, only_unawarded=only_unawarded)

    def action_compare(self):
        self.line_ids._rfq_compute_scores()
        return super().action_compare()

    def action_award_best_score(self):
        self._check_can_award()
        self.line_ids._rfq_compute_scores()
        for line in self.line_ids:
            line._award(line._get_best_quote("score"))
        return True
