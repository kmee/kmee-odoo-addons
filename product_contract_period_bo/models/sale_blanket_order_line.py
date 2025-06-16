# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleBlanketOrderLine(models.Model):

    _inherit = "sale.blanket.order.line"

    period_qty = fields.Float(
        string="Quantidade por Período",
        default=1.0,
        help="Quantidade fornecida em cada período",
    )
    period_count = fields.Integer(
        string="Número de Períodos", default=1, help="Número total de períodos"
    )
    period_amount = fields.Monetary(
        string="Valor por Período",
        store=True,
        help="Valor por período = Qtd * (Valor Unitário - Desconto)",
    )
    recurring_rule_type = fields.Selection(
        [
            ("daily", "Day(s)"),
            ("weekly", "Week(s)"),
            ("monthly", "Month(s)"),
            ("monthlylastday", "Month(s) last day"),
            ("quarterly", "Quarter(s)"),
            ("semesterly", "Semester(s)"),
            ("yearly", "Year(s)"),
        ],
        store=True,
        readonly=False,
        required=False,
        copy=True,
    )
    date_start = fields.Date()
    date_end = fields.Date()
