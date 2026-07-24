from odoo import fields, models


class ESocialFinanciamentoAposent(models.Model):
    _name = "l10n_br.esocial.financiamento.aposent"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 02 - Financiamento Aposentadoria Especial"


class ESocialTipoInscricao(models.Model):
    _name = "l10n_br.esocial.tipo.inscricao"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 05 - Tipos de Inscrição"


class ESocialPais(models.Model):
    _name = "l10n_br.esocial.pais"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 06 - Países"


class ESocialTipoArquivo(models.Model):
    _name = "l10n_br.esocial.tipo.arquivo"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 09 - Tipos de Arquivo/Evento"

    id_tp_evento = fields.Char()
    tag_tp_evento = fields.Char()
    identificador = fields.Char()


class ESocialTipoLogradouro(models.Model):
    _name = "l10n_br.esocial.tipo.logradouro"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 20 - Tipos de Logradouro"


class ESocialTipoDependente(models.Model):
    _name = "l10n_br.esocial.tipo.dependente"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 25 - Tipos de Dependente"


class ESocialHorario(models.Model):
    _name = "l10n_br.esocial.horario"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 52 - Horários"

    hr_entrada = fields.Char()
    hr_saida = fields.Char()
    dur_jornada = fields.Char()
    tp_intervalo = fields.Char()
    dur_intervalo = fields.Char()
    ini_intervalo = fields.Char()
    term_intervalo = fields.Char()
    horario_flexivel = fields.Char()
    qtd_hrs_semana = fields.Char()


class ESocialTipoCat(models.Model):
    _name = "l10n_br.esocial.tipo.cat"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 71 - Tipos de CAT"


class ESocialTipoAso(models.Model):
    _name = "l10n_br.esocial.tipo.aso"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 72 - Tipos de ASO"


class ESocialTipoAvisoPrevio(models.Model):
    _name = "l10n_br.esocial.tipo.aviso.previo"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 73 - Tipos de Aviso Prévio"


class ESocialMotivoCancelAviso(models.Model):
    _name = "l10n_br.esocial.motivo.cancel.aviso"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 74 - Motivos Cancelamento Aviso Prévio"


class ESocialFeriado(models.Model):
    _name = "l10n_br.esocial.feriado"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 84 - Feriados"
