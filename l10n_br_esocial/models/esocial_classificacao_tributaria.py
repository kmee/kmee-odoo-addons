# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESocialClassificacaoTributaria(models.Model):
    _name = "l10n_br.esocial.classificacao.tributaria"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 8 - Classificação Tributária"
    _order = "codigo"

    tp_insc = fields.Char()
