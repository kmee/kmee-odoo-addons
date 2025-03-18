# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ContractContract(models.Model):
    _inherit = "contract.contract"

    # Campos de resumo para valores por período
    monthly_value = fields.Monetary(
        string="Valor Mensal",
        compute="_compute_period_values",
        store=True,
        help="Valor médio mensal do contrato",
    )
    annual_value = fields.Monetary(
        string="Valor Anual",
        compute="_compute_period_values",
        store=True,
        help="Valor anual estimado do contrato",
    )
    total_contract_value = fields.Monetary(
        string="Valor Total do Contrato", compute="_compute_period_values", store=True
    )
    current_month_value = fields.Monetary(
        string="Valor do Mês Atual",
        compute="_compute_period_values",
        store=True,
        help="Valor total das linhas ativas no mês corrente",
    )

    @api.depends(
        "contract_line_ids",
        "contract_line_ids.price_unit",
        "contract_line_ids.period_qty",
        "contract_line_ids.period_count",
        "contract_line_ids.recurring_rule_type",
        "contract_line_ids.date_start",
        "contract_line_ids.date_end",
    )
    def _compute_period_values(self):
        for contract in self:
            active_lines = contract.contract_line_ids.filtered(
                lambda line: not line.is_canceled and not line.display_type
            )

            # Valor total do contrato (soma do total de todas as linhas)
            contract.total_contract_value = sum(
                line.total_amount for line in active_lines
            )

            # Cálculo do valor mensal (média ponderada por período)
            total_months = 0
            total_weighted_value = 0.0

            for line in active_lines:
                # Converter período para meses
                if line.recurring_rule_type == "daily":
                    months = line.period_count / 30
                elif line.recurring_rule_type == "weekly":
                    months = line.period_count / 4.33
                elif line.recurring_rule_type == "monthly":
                    months = line.period_count
                elif line.recurring_rule_type == "quarterly":
                    months = line.period_count * 3
                elif line.recurring_rule_type == "semesterly":
                    months = line.period_count * 6
                elif line.recurring_rule_type == "yearly":
                    months = line.period_count * 12
                else:
                    months = 0

                total_months += months
                total_weighted_value += line.total_amount

            # Calcular valor mensal médio
            if total_months:
                contract.monthly_value = total_weighted_value / total_months
                contract.annual_value = contract.monthly_value * 12
            else:
                contract.monthly_value = 0
                contract.annual_value = 0

            # Calcular valor do mês corrente usando a data da próxima fatura
            next_invoice_date = contract.recurring_next_date
            current_month_lines = active_lines.filtered(
                lambda line: line.date_start <= next_invoice_date <= line.date_end
            )

            current_month_value = sum(
                line.period_amount for line in current_month_lines
            )

            contract.current_month_value = current_month_value

    # Relatório de distribuição de valor por período
    def generate_period_distribution_report(self):
        self.ensure_one()

        # Preparar dados para o relatório
        data = {
            "contract_id": self.id,
            "name": self.name,
            "partner_id": self.partner_id.id,
            "monthly_value": self.monthly_value,
            "annual_value": self.annual_value,
            "total_value": self.total_contract_value,
            "line_details": [],
        }

        # Obter detalhes de linha por período
        for line in self.contract_line_ids.filtered(
            lambda line_item: not line_item.is_canceled and not line_item.display_type
        ):
            # Calcular valor por período
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            period_value = price * line.period_qty

            data["line_details"].append(
                {
                    "product": line.product_id.name,
                    "period_qty": line.period_qty,
                    "period_count": line.period_count,
                    "period_value": period_value,
                    "total_line_value": period_value * line.period_count,
                    "date_start": line.date_start,
                    "date_end": line.date_end,
                }
            )

        # Retornar ação para exibir relatório
        return {
            "type": "ir.actions.report",
            "report_name": "contract.report_contract_period_distribution",
            "report_type": "qweb-pdf",
            "data": data,
        }
