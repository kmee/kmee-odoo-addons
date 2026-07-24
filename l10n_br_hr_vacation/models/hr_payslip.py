# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

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
    l10n_br_avos_ferias = fields.Integer(
        string="Avos de Férias Proporcionais",
        compute="_compute_avos_ferias",
        help="Meses (fração >= 15 dias) do período aquisitivo em curso, "
        "usados para as férias proporcionais na rescisão.",
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

    @api.depends("contract_id", "date_to")
    def _compute_avos_ferias(self):
        for rec in self:
            if rec.contract_id and rec.contract_id.date_start and rec.date_to:
                rec.l10n_br_avos_ferias = self._calc_avos_ferias_proporcionais(
                    rec.contract_id.date_start, rec.date_to
                )
            else:
                rec.l10n_br_avos_ferias = 0

    @staticmethod
    def _calc_avos_ferias_proporcionais(data_admissao, data_referencia):
        """Avos de férias proporcionais do período aquisitivo em curso.

        Conta os meses (alinhados ao aniversário de admissão) com fração
        igual ou superior a 15 dias, desde o início do período aquisitivo
        em curso (último aniversário de admissão <= referência) até a data
        de referência (rescisão). Máximo de 12 avos.

        Nota: NÃO considera férias vencidas de períodos aquisitivos
        completos e não gozados — ver relatório (lacuna).
        """
        anos = data_referencia.year - data_admissao.year
        inicio = data_admissao + relativedelta(years=anos)
        if inicio > data_referencia:
            inicio = data_admissao + relativedelta(years=anos - 1)
        avos = 0
        cursor = inicio
        while cursor <= data_referencia:
            fim_mes = cursor + relativedelta(months=1) - relativedelta(days=1)
            if fim_mes <= data_referencia:
                avos += 1
            else:
                dias = (data_referencia - cursor).days + 1
                if dias >= 15:
                    avos += 1
            cursor += relativedelta(months=1)
        return min(avos, 12)

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
            "ADICIONAL_ABONO",
            "DECIMO_TERCEIRO_BRUTO",
            "ADIANTAMENTO_13",
            "INSS_13",
            "IRRF_13",
            "BASE_IRRF_13",
            "DECIMO_RESCISAO",
            "SALDO_SALARIO",
            "FERIAS_INDENIZADAS",
            "ADICIONAL_FERIAS_INDENIZADAS",
        ):
            localdict.setdefault(code, 0.0)
        return localdict
