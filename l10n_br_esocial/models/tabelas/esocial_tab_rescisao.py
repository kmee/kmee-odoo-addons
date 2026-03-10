from odoo import fields, models


class ESocialReceitaReclamatoria(models.Model):
    _name = "l10n_br.esocial.receita.reclamatoria"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 32 - Receita Reclamatória Trabalhista"


class ESocialMotivoCessacao(models.Model):
    _name = "l10n_br.esocial.motivo.cessacao"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 34 - Motivos Cessação de Benefícios"


class ESocialCausaAfastMte(models.Model):
    _name = "l10n_br.esocial.causa.afast.mte"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 67 - Causas de Afastamento MTE"

    cod_esocial = fields.Char()


class ESocialRubricaRescisoria(models.Model):
    _name = "l10n_br.esocial.rubrica.rescisoria"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 68 - Rubricas Rescisórias MTE"

    cod_rubrica_esocial = fields.Char()
    campo_fixo = fields.Char()
    restricao_nao_exibir = fields.Char()


class ESocialInfoRescisao(models.Model):
    _name = "l10n_br.esocial.info.rescisao"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 69 - Informações Adicionais Rescisão MTE"
