from odoo import fields, models


class ESocialLotacaoTributaria(models.Model):
    _name = "l10n_br.esocial.lotacao.tributaria"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 10 - Tipos de Lotação Tributária"
    _order = "codigo"

    tp_inscr = fields.Char()
    nr_inscr = fields.Char()
    cd_valid = fields.Char()
    tx_class_trb = fields.Char()
