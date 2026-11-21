# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseRfqRoundAward(models.TransientModel):
    _name = "purchase.rfq.round.award"
    _description = "Award Quotation Round"

    round_id = fields.Many2one("purchase.rfq.round", required=True)
    criterion = fields.Selection(
        [("price", "Best price"), ("date", "Best lead time")],
        required=True,
        default=lambda self: self._default_criterion(),
    )
    only_unawarded = fields.Boolean(
        string="Keep current choices",
        default=True,
        help="Adjudica só os itens ainda sem vencedor; as escolhas já feitas, "
        "inclusive à mão na comparação, ficam.",
    )
    line_count = fields.Integer(related="round_id.line_count")
    awarded_line_count = fields.Integer(related="round_id.awarded_line_count")

    def _default_criterion(self):
        return "price"

    def action_apply(self):
        self.ensure_one()
        self.round_id._award_lines(self.criterion, self.only_unawarded)
        return {"type": "ir.actions.act_window_close"}
