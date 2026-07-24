# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESocialNaturezaRubrica(models.Model):
    _name = "l10n_br.esocial.natureza.rubrica"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 3 - Natureza da Rubrica"
    _order = "codigo"

    descricao = fields.Text()
    incidencia_exclusiva_empregado = fields.Char()
