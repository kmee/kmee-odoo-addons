from odoo import fields, models


class ESocialParteCorpo(models.Model):
    _name = "l10n_br.esocial.parte.corpo"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 13 - Parte do Corpo Atingida"


class ESocialAgenteCausador(models.Model):
    _name = "l10n_br.esocial.agente.causador"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 14 - Agente Causador de Acidente de Trabalho"


class ESocialSituacaoGeradora(models.Model):
    _name = "l10n_br.esocial.situacao.geradora"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 15 - Situação Geradora de Acidente de Trabalho"

    aplicacao = fields.Char()


class ESocialNaturezaLesao(models.Model):
    _name = "l10n_br.esocial.natureza.lesao"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 17 - Natureza da Lesão"
