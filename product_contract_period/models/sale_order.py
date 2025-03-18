# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Método para calcular o valor total considerando períodos
    @api.depends(
        "order_line.period_qty", "order_line.price_unit", "order_line.discount"
    )
    def _compute_total_by_period(self):
        for order in self:
            contract_lines = order.order_line.filtered(
                lambda line: line.product_id.is_contract
            )
            if contract_lines:
                period_contract_value = sum(
                    line.price_unit
                    * line.period_qty
                    * (1 - (line.discount or 0.0) / 100.0)
                    for line in contract_lines
                )
                order.period_contract_value = period_contract_value
            else:
                order.period_contract_value = 0.0

    period_contract_value = fields.Monetary(
        string="Valor por periodo",
        compute="_compute_total_by_period",
        store=True,
        help="Valor mensal estimado dos serviços recorrentes.",
    )

    contract_periods = fields.Integer(
        compute="_compute_contract_periods",
        string="Períodos de Contrato",
        store=True,
        help="Número total de períodos para todos os contratos",
    )

    contract_period_details = fields.Text(
        compute="_compute_contract_periods", string="Detalhes de Períodos", store=True
    )

    contract_average_value = fields.Monetary(
        compute="_compute_contract_periods", string="Valor Médio Mensal", store=True
    )

    @api.depends(
        "order_line.period_qty",
        "order_line.period_count",
        "order_line.price_unit",
        "order_line.discount",
    )
    def _compute_contract_periods(self):
        for order in self:
            contract_lines = order.order_line.filtered(
                lambda line: line.product_id.is_contract
            )
            total_periods = sum(line.period_count for line in contract_lines)
            order.contract_periods = total_periods

            # Calcular valor médio mensal
            if contract_lines:
                # Calcular valor total dos contratos
                total_contract_value = sum(
                    line.price_unit
                    * line.period_qty
                    * line.period_count
                    * (1 - (line.discount or 0.0) / 100.0)
                    for line in contract_lines
                )

                # Calcular duração total em meses
                total_months = 0
                for line in contract_lines:
                    if line.recurring_rule_type == "daily":
                        months = (line.period_count * 1) / 30  # 1 dia
                    elif line.recurring_rule_type == "weekly":
                        months = (line.period_count * 7) / 30  # 7 dias
                    elif line.recurring_rule_type == "monthly":
                        months = line.period_count * 1  # 1 mês
                    elif line.recurring_rule_type == "quarterly":
                        months = line.period_count * 3  # 3 meses
                    elif line.recurring_rule_type == "semesterly":
                        months = line.period_count * 6  # 6 meses
                    elif line.recurring_rule_type == "yearly":
                        months = line.period_count * 12  # 12 meses
                    else:
                        months = line.period_count
                    total_months += months

                if total_months:
                    order.contract_average_value = total_contract_value / total_months
                else:
                    order.contract_average_value = order.period_contract_value

                # Construir detalhes dos períodos
                details = []
                for line in contract_lines:
                    period_value = (
                        line.price_unit
                        * line.period_qty
                        * (1 - (line.discount or 0.0) / 100.0)
                    )
                    details.append(
                        _(
                            """%(product)s: %(period_value)s x %(period_count)s
                             períodos (%(rule_type)s) = %(total)s"""
                        )
                        % {
                            "product": line.product_id.name,
                            "period_value": period_value,
                            "period_count": line.period_count,
                            "rule_type": line.recurring_rule_type,
                            "total": period_value * line.period_count,
                        }
                    )
                order.contract_period_details = "\n".join(details)
            else:
                order.contract_average_value = 0
                order.contract_period_details = ""

    def get_period_values_for_print(self):
        self.ensure_one()
        result = {
            "contract_lines": [],
            "total_periods": self.contract_periods,
            "average_monthly": self.contract_average_value,
        }

        for line in self.order_line.filtered(lambda line: line.product_id.is_contract):
            period_value = (
                line.price_unit * line.period_qty * (1 - (line.discount or 0.0) / 100.0)
            )
            result["contract_lines"].append(
                {
                    "name": line.name,
                    "period_qty": line.period_qty,
                    "period_count": line.period_count,
                    "period_type": line.recurring_rule_type,
                    "period_value": period_value,
                    "total_value": period_value * line.period_count,
                }
            )

        return result
