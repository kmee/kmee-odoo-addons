# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from . import regras_jornada


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_br_tolerancia_marcacao = fields.Integer(
        string="Tolerância por marcação (min)",
        default=regras_jornada.TOLERANCIA_POR_MARCACAO,
        help="Art. 58, § 1º da CLT. O padrão legal é 5 minutos por marcação.",
    )
    l10n_br_tolerancia_diaria = fields.Integer(
        string="Tolerância diária (min)",
        default=regras_jornada.TOLERANCIA_DIARIA,
        help="Art. 58, § 1º da CLT. O padrão legal é 10 minutos no dia. "
        "Ultrapassado o limite, computa-se o tempo integral (Súmula 366 do TST).",
    )
    l10n_br_intrajornada_minima = fields.Integer(
        string="Intervalo intrajornada mínimo (min)",
        default=regras_jornada.INTRAJORNADA_MINIMA_ACIMA_6H,
        help="Mínimo para jornadas acima de 6h. Convenção ou acordo coletivo "
        "pode reduzir até 30 minutos (art. 611-A, III da CLT); abaixo disso o "
        "sistema mantém o piso de 30.",
    )
    l10n_br_bloqueia_holerite_divergente = fields.Boolean(
        string="Bloquear holerite divergente da apuração",
        default=True,
        help="Impede validar holerite cujos valores de jornada não batem com "
        "a apuração fechada da competência, salvo justificativa registrada.",
    )
