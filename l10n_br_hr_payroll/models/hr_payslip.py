# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import types

from odoo import fields, models

from . import salary_rules_br


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    l10n_br_horas_extras_50 = fields.Float(
        string="Horas Extras 50%",
        help="Horas extras em dias úteis",
    )
    l10n_br_horas_extras_100 = fields.Float(
        string="Horas Extras 100%",
        help="Horas extras em domingos/feriados",
    )
    l10n_br_horas_noturnas = fields.Float(
        string="Horas Noturnas",
        help="Horas trabalhadas entre 22h e 05h",
    )
    l10n_br_usar_hora_reduzida = fields.Boolean(
        string="Usar Hora Noturna Reduzida",
        help="Hora noturna = 52min30s (7/8 da hora normal)",
    )
    l10n_br_horas_noturnas_computadas = fields.Float(
        string="Horas Noturnas Computadas",
        compute="_compute_horas_noturnas_computadas",
    )
    l10n_br_faltas_injustificadas = fields.Integer(
        string="Faltas Injustificadas",
        default=0,
    )

    def _compute_horas_noturnas_computadas(self):
        for rec in self:
            if rec.l10n_br_usar_hora_reduzida:
                rec.l10n_br_horas_noturnas_computadas = (
                    rec.l10n_br_horas_noturnas * 7 / 8
                )
            else:
                rec.l10n_br_horas_noturnas_computadas = rec.l10n_br_horas_noturnas

    def _get_tools_dict(self):
        tools = super()._get_tools_dict()
        tools["br"] = types.SimpleNamespace(
            calc_inss=salary_rules_br.calc_inss,
            calc_irrf=salary_rules_br.calc_irrf,
            calc_ferias_dias=salary_rules_br.calc_ferias_dias,
            calc_decimo_avos=salary_rules_br.calc_decimo_avos,
            calc_vt=salary_rules_br.calc_vt,
            calc_salario_familia=salary_rules_br.calc_salario_familia,
            IRRF_DEDUCAO_DEPENDENTE=salary_rules_br.IRRF_DEDUCAO_DEPENDENTE,
            SALARIO_MINIMO=salary_rules_br.SALARIO_MINIMO,
        )
        return tools
