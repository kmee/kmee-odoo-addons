# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class L10nBrHrMarcacao(models.Model):
    _inherit = "l10n_br.hr.marcacao"

    apuracao_dia_id = fields.Many2one(
        comodel_name="l10n_br.hr.apuracao.dia",
        string="Apuração do dia",
        ondelete="set null",
        index=True,
    )
