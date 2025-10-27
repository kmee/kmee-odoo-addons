# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class ContractLine(models.Model):
    _inherit = "contract.line"

    # Adicionando campos de períodos
    period_qty = fields.Float(
        string="Quantidade de Licenças",
        default=1.0,
        help="Quantidade de licenças fornecida em cada período",
    )
    period_count = fields.Integer(
        string="Meses", default=1, help="Número total de meses"
    )
    period_amount = fields.Monetary(
        string="Valor por Período", compute="_compute_period_amount", store=True
    )
    total_amount = fields.Monetary(
        string="Valor Total", compute="_compute_period_amount", store=True
    )

    # Sobrescrever o método de cálculo de data final para considerar período_count
    @api.onchange(
        "date_start", "period_count", "recurring_rule_type", "recurring_interval"
    )
    def _onchange_date_start(self):
        for rec in self:
            if not rec.date_start:
                return
            date_end = rec.date_start
            if rec.recurring_rule_type == "daily":
                date_end = (
                    rec.date_start
                    + relativedelta(days=(rec.recurring_interval * rec.period_count))
                    - relativedelta(days=1)
                )
            elif rec.recurring_rule_type == "weekly":
                date_end = (
                    rec.date_start
                    + relativedelta(weeks=(rec.recurring_interval * rec.period_count))
                    - relativedelta(days=1)
                )
            elif rec.recurring_rule_type == "monthly":
                date_end = (
                    rec.date_start
                    + relativedelta(months=(rec.recurring_interval * rec.period_count))
                    - relativedelta(days=1)
                )
            elif rec.recurring_rule_type == "monthlylastday":
                date_end = (
                    rec.date_start
                    + relativedelta(
                        months=(rec.recurring_interval * rec.period_count), day=31
                    )
                    - relativedelta(days=1)
                )
            elif rec.recurring_rule_type == "quarterly":
                date_end = (
                    rec.date_start
                    + relativedelta(
                        months=(rec.recurring_interval * 3 * rec.period_count)
                    )
                    - relativedelta(days=1)
                )
            elif rec.recurring_rule_type == "semesterly":
                date_end = (
                    rec.date_start
                    + relativedelta(
                        months=(rec.recurring_interval * 6 * rec.period_count)
                    )
                    - relativedelta(days=1)
                )
            elif rec.recurring_rule_type == "yearly":
                date_end = (
                    rec.date_start
                    + relativedelta(years=(rec.recurring_interval * rec.period_count))
                    - relativedelta(days=1)
                )
            rec.date_end = date_end

    @api.depends(
        "period_qty", "price_unit", "discount", "period_count", "date_start", "date_end"
    )
    def _compute_period_amount(self):
        for line in self:
            price_with_discount = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            line.period_amount = line.period_qty * price_with_discount
            line.total_amount = line.period_amount * line.period_count

    # Sobrescrever método para preparar os valores de faturamento
    def _prepare_invoice_line(self):
        self.ensure_one()
        values = super()._prepare_invoice_line()
        if values and self.period_qty:
            values.update(
                {
                    "quantity": self.period_qty,
                    "price_unit": self.price_unit,
                    "price_subtotal": self.period_amount,
                }
            )
        return values
