# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from .constantes_rh import CENTRALIZADORA


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_br_codigo_outras_entidades = fields.Char(
        string="Código Outras Entidades (SEFIP)",
        size=4,
        help="Código de terceiros/outras entidades (Salário Educação, INCRA, SESCOOP)",
    )
    l10n_br_codigo_recolhimento_gps = fields.Char(
        string="Código Recolhimento GPS",
        size=4,
    )
    l10n_br_codigo_fpas = fields.Char(
        string="Código FPAS",
        size=3,
        default="515",
        help="Fundo de Previdência e Assistência Social",
    )
    l10n_br_centralizadora = fields.Selection(
        selection=CENTRALIZADORA,
        string="Centralização FGTS",
        default="0",
    )
    l10n_br_porcentagem_filantropia = fields.Float(
        string="Porcentagem Filantropia (%)",
        help="Percentual de isenção de filantropia para FPAS 639",
    )
