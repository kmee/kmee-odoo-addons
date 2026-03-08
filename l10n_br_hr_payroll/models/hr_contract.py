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
