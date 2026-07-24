from odoo import fields, models


class ESocialNaturezaRubrica(models.Model):
    _name = "l10n_br.esocial.natureza.rubrica"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 3 - Natureza da Rubrica"
    _order = "codigo"

    descricao = fields.Text()
    incidencia_exclusiva_empregado = fields.Char()
