from odoo import fields, models


class ESocialCategoriaTrabalhador(models.Model):
    _name = "l10n_br.esocial.categoria.trabalhador"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 1 - Categoria do Trabalhador"
    _order = "codigo"

    grupo = fields.Char()
    aliq_fgts = fields.Char()
    obriga = fields.Char()
    aliq_fgts_co = fields.Char()
    cp = fields.Char()
    emprestimo_consignado = fields.Char()
