# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESocialFinanciamentoAposent(models.Model):
    _name = "l10n_br.esocial.financiamento.aposent"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 02 - Financiamento Aposentadoria Especial"


class ESocialTipoInscricao(models.Model):
    _name = "l10n_br.esocial.tipo.inscricao"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 05 - Tipos de Inscrição"


class ESocialPais(models.Model):
    _name = "l10n_br.esocial.pais"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 06 - Países"


class ESocialTipoArquivo(models.Model):
    _name = "l10n_br.esocial.tipo.arquivo"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 09 - Tipos de Arquivo/Evento"

    id_tp_evento = fields.Char()
    tag_tp_evento = fields.Char()
    identificador = fields.Char()


class ESocialTipoLogradouro(models.Model):
    _name = "l10n_br.esocial.tipo.logradouro"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 20 - Tipos de Logradouro"


class ESocialTipoDependente(models.Model):
    _name = "l10n_br.esocial.tipo.dependente"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 07 - Tipos de Dependente"


class ESocialHorario(models.Model):
    _name = "l10n_br.esocial.horario"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial - Horários"

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
    _description = "eSocial - Tipos de CAT (tpCat do S-2210)"


class ESocialTipoAso(models.Model):
    _name = "l10n_br.esocial.tipo.aso"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial - Tipos de ASO (tpExameOcup do S-2220)"


class ESocialTipoAvisoPrevio(models.Model):
    _name = "l10n_br.esocial.tipo.aviso.previo"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial - Tipos de Aviso Prévio"


class ESocialMotivoCancelAviso(models.Model):
    _name = "l10n_br.esocial.motivo.cancel.aviso"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial - Motivos Cancelamento Aviso Prévio"


class ESocialFeriado(models.Model):
    _name = "l10n_br.esocial.feriado"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "Feriados Nacionais"
    # Só os feriados nacionais (Lei 662/1949, Lei 6.802/1980 e Lei
    # 14.759/2023). Carnaval, Sexta-feira da Paixão e Corpus Christi não são
    # feriados nacionais; feriado estadual ou municipal é configuração local.
    # Não existe tabela de feriados no Anexo I do eSocial.
