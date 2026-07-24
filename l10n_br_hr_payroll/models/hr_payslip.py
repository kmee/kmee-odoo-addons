# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import types

from odoo import api, fields, models

from . import salary_rules_br

_logger = logging.getLogger(__name__)


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

    def compute_sheet(self):
        """Ensure worked_days_line_ids are populated before computing rules.

        OCA compute_sheet() only computes salary rule lines (line_ids).
        worked_days are normally populated by onchange handlers (UI) or the
        batch wizard, but NOT by compute_sheet itself. When payslips are
        created programmatically (tests, demo, API), worked_days are empty.
        This override fills them in if missing.
        """
        for payslip in self:
            if not payslip.worked_days_line_ids:
                contracts = payslip._get_employee_contracts()
                if contracts and payslip.date_from and payslip.date_to:
                    worked_days = payslip.get_worked_day_lines(
                        contracts, payslip.date_from, payslip.date_to
                    )
                    lines = [(0, 0, wd) for wd in worked_days]
                    payslip.write({"worked_days_line_ids": lines})
        return super().compute_sheet()

    def _get_baselocaldict(self, contracts):
        """Pre-populate rule codes with 0.0 defaults.

        Rules with conditional execution (e.g. FALTAS only when faltas > 0)
        may not fire, leaving their code absent from localdict. Pre-populating
        ensures downstream rules can safely reference them without NameError.
        """
        localdict = super()._get_baselocaldict(contracts)
        for code in (
            "FALTAS",
            "DESC_DSR",
            "INSS",
            "CONTRIB_RPPS",
            "BASE_IRRF",
        ):
            localdict.setdefault(code, 0.0)
        return localdict

    def _get_tools_dict(self):
        tools = super()._get_tools_dict()
        tools["br"] = types.SimpleNamespace(
            round_money=salary_rules_br.round_money,
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

    @api.model
    def _demo_compute_payslips(self):
        """Compute all draft demo payslips. Called from demo XML via <function>."""
        payslips = self.search([("state", "=", "draft")])
        for slip in payslips:
            try:
                slip.compute_sheet()
            except Exception:
                _logger.warning(
                    "Demo: falha ao calcular holerite %s", slip.name, exc_info=True
                )
        _logger.info("Demo: %d holerites calculados", len(payslips))
