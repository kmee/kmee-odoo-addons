# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseRfqRoundResponse(models.Model):
    """Resposta original do fornecedor, como veio, antes de qualquer ajuste.

    A cotação (RFQ) guarda o valor vigente; esta tabela guarda o histórico:
    cada importação ou digitação gera uma linha, e a rodada seguinte não apaga
    as respostas da anterior.
    """

    _name = "purchase.rfq.round.response"
    _description = "Quotation Round Vendor Response"
    _order = "round_id, id"

    round_id = fields.Many2one(
        "purchase.rfq.round", required=True, ondelete="cascade", index=True
    )
    round_line_id = fields.Many2one(
        "purchase.rfq.round.line", ondelete="set null", index=True
    )
    order_id = fields.Many2one("purchase.order", ondelete="set null", index=True)
    order_line_id = fields.Many2one("purchase.order.line", ondelete="set null")
    partner_id = fields.Many2one("res.partner", string="Vendor", required=True)
    product_id = fields.Many2one("product.product")
    company_id = fields.Many2one(related="round_id.company_id", store=True)
    currency_id = fields.Many2one(related="round_id.currency_id")
    price_unit = fields.Float(digits="Product Price")
    delay = fields.Integer(string="Lead Time (days)")
    note = fields.Char()
    source = fields.Selection(
        [("import", "Spreadsheet"), ("manual", "Manual")],
        default="import",
        required=True,
    )
    file_name = fields.Char()
    raw_values = fields.Json(help="Valores da linha como vieram na planilha.")
