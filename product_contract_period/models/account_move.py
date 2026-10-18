# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # Campos para rastrear períodos em faturas
    contract_period_number = fields.Integer(
        string="Período Nº", help="Número do período da assinatura para esta fatura"
    )

    contract_period_total = fields.Integer(
        string="Total de Períodos",
        help="Número total de períodos do contrato relacionado",
    )

    # Adicionar informações de períodos ao criar faturas a partir de contratos
    @api.model
    def _prepare_invoice_from_contract(self, contract, date_invoice):
        vals = super(AccountMove, self)._prepare_invoice_from_contract(
            contract, date_invoice
        )

        # Adicionar período atual
        active_lines = contract.contract_line_ids.filtered(
            lambda line: not line.is_canceled
        )
        if active_lines:
            # Encontrar posição relativa do período atual
            period_count = 0
            period_total = 0

            for line in active_lines:
                if line.date_start and line.date_end and line.period_count:
                    period_total += line.period_count

                    # Estimar em qual período estamos
                    if date_invoice >= line.date_start:
                        # Calcular o período atual com base na data de fatura
                        start_date = line.date_start
                        if line.recurring_rule_type == "daily":
                            days_passed = (date_invoice - start_date).days
                            period_count = (days_passed // line.recurring_interval) + 1
                        elif line.recurring_rule_type == "weekly":
                            weeks_passed = (date_invoice - start_date).days // 7
                            period_count = (weeks_passed // line.recurring_interval) + 1
                        elif line.recurring_rule_type == "monthly":
                            months_passed = (
                                (date_invoice.year - start_date.year) * 12
                                + date_invoice.month
                                - start_date.month
                            )
                            period_count = (
                                months_passed // line.recurring_interval
                            ) + 1
                        elif line.recurring_rule_type == "quarterly":
                            months_passed = (
                                (date_invoice.year - start_date.year) * 12
                                + date_invoice.month
                                - start_date.month
                            )
                            period_count = (
                                months_passed // (3 * line.recurring_interval)
                            ) + 1
                        elif line.recurring_rule_type == "semesterly":
                            months_passed = (
                                (date_invoice.year - start_date.year) * 12
                                + date_invoice.month
                                - start_date.month
                            )
                            period_count = (
                                months_passed // (6 * line.recurring_interval)
                            ) + 1
                        elif line.recurring_rule_type == "yearly":
                            years_passed = date_invoice.year - start_date.year
                            period_count = (years_passed // line.recurring_interval) + 1

                        period_count = min(period_count, line.period_count)

            # Adicionar campos à fatura
            vals.update(
                {
                    "contract_period_number": period_count,
                    "contract_period_total": period_total // len(active_lines)
                    if active_lines
                    else 0,
                }
            )

        return vals
