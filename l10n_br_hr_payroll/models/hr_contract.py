# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = "hr.contract"

    l10n_br_periculosidade = fields.Boolean(
        string="Periculosidade",
        help="Adicional de periculosidade (30% do salário base)",
    )
    l10n_br_insalubridade = fields.Boolean(
        string="Insalubridade",
    )
    l10n_br_grau_insalubridade = fields.Selection(
        selection=[
            ("minimo", "Mínimo (10%)"),
            ("medio", "Médio (20%)"),
            ("maximo", "Máximo (40%)"),
        ],
        string="Grau de Insalubridade",
    )

    # Divisor mensal padrão CLT (44h semanais × 5): usado como fallback
    # quando o contrato não tem calendário de trabalho configurado.
    _L10N_BR_DIVISOR_PADRAO = 220.0

    def _l10n_br_horas_semanais(self):
        """Horas contratuais semanais derivadas do calendário de trabalho.

        Soma a jornada das linhas de presença (``attendance_ids``) de uma
        semana. Em calendários de duas semanas (``two_weeks_calendar``) a soma
        é dividida por 2 para obter a média semanal.

        Returns:
            Horas semanais (float); ``0.0`` se não houver calendário/jornada.
        """
        self.ensure_one()
        calendar = self.resource_calendar_id
        if not calendar or not calendar.attendance_ids:
            return 0.0
        attendances = calendar.attendance_ids
        total = sum(a.hour_to - a.hour_from for a in attendances)
        if any(attendances.mapped("two_weeks_calendar")):
            total /= 2.0
        return total

    def _l10n_br_divisor_horas_mensais(self):
        """Divisor mensal de horas para cálculo do salário-hora (RF-26).

        Deriva da jornada do contrato: ``horas_semanais × 5`` (equivale a
        ``horas_semanais / 6 × 30`` da CLT — 44h → 220, 40h → 200). Quando o
        contrato não tem calendário/jornada, usa o divisor padrão de 220.
        """
        self.ensure_one()
        horas_semanais = self._l10n_br_horas_semanais()
        if not horas_semanais:
            return self._L10N_BR_DIVISOR_PADRAO
        return horas_semanais * 5.0

    @api.constrains("l10n_br_periculosidade", "l10n_br_insalubridade")
    def _check_periculosidade_insalubridade(self):
        """Periculosidade e insalubridade não acumulam (Súmula 364 TST)."""
        for rec in self:
            if rec.l10n_br_periculosidade and rec.l10n_br_insalubridade:
                raise ValidationError(
                    _(
                        "Não é permitido acumular periculosidade e insalubridade "
                        "(Súmula 364 do TST)."
                    )
                )
