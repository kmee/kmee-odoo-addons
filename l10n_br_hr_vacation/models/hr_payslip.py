# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    l10n_br_abono_pecuniario = fields.Boolean(
        string="Abono Pecuniário",
        help="Venda de 1/3 dos dias de férias (CLT art. 143)",
    )
    l10n_br_dias_ferias_gozadas = fields.Integer(
        string="Dias de Férias Gozadas",
        compute="_compute_dias_ferias_gozadas",
    )
    l10n_br_avos_13 = fields.Integer(
        string="Avos de 13º",
        compute="_compute_avos_13",
    )
    l10n_br_primeira_parcela_13_paga = fields.Float(
        string="1ª Parcela do 13º já paga",
        help="Valor da 1ª parcela do 13º já paga (para cálculo da 2ª parcela)",
    )
    l10n_br_liquido_13 = fields.Float(
        string="Líquido 13º",
        compute="_compute_liquido_13",
    )

    @api.depends("l10n_br_abono_pecuniario")
    def _compute_dias_ferias_gozadas(self):
        for rec in self:
            if rec.l10n_br_abono_pecuniario:
                rec.l10n_br_dias_ferias_gozadas = 20
            else:
                rec.l10n_br_dias_ferias_gozadas = 30

    @api.depends("contract_id", "date_to")
    def _compute_avos_13(self):
        from odoo.addons.l10n_br_hr_payroll.models.salary_rules_br import (
            calc_decimo_avos,
        )

        for rec in self:
            if rec.contract_id and rec.date_to:
                rec.l10n_br_avos_13 = calc_decimo_avos(
                    rec.contract_id.date_start, rec.date_to
                )
            else:
                rec.l10n_br_avos_13 = 0

    @api.depends("line_ids", "l10n_br_primeira_parcela_13_paga")
    def _compute_liquido_13(self):
        for rec in self:
            bruto = sum(
                rec.line_ids.filtered(
                    lambda line: line.code == "DECIMO_TERCEIRO_BRUTO"
                ).mapped("total")
            )
            inss_13 = sum(
                rec.line_ids.filtered(lambda line: line.code == "INSS_13").mapped(
                    "total"
                )
            )
            irrf_13 = sum(
                rec.line_ids.filtered(lambda line: line.code == "IRRF_13").mapped(
                    "total"
                )
            )
            rec.l10n_br_liquido_13 = (
                bruto - inss_13 - irrf_13 - rec.l10n_br_primeira_parcela_13_paga
            )

    def _get_baselocaldict(self, contracts):
        localdict = super()._get_baselocaldict(contracts)
        for code in (
            "FERIAS",
            "ADICIONAL_FERIAS",
            "ABONO_PECUNIARIO",
            "DECIMO_TERCEIRO_BRUTO",
            "ADIANTAMENTO_13",
            "INSS_13",
            "IRRF_13",
            "DECIMO_RESCISAO",
        ):
            localdict.setdefault(code, 0.0)
        return localdict
