# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESocialAgenteNocivo(models.Model):
    _name = "l10n_br.esocial.agente.nocivo"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 24 - Agentes Nocivos e Atividades"

    tipo = fields.Char()


class ESocialAposentadoriaEspecial(models.Model):
    _name = "l10n_br.esocial.aposentadoria.especial"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "Aposentadoria Especial - Anexo IV do Decreto 3.048/1999"

    tempo_contribuicao = fields.Char()
    aliquota = fields.Char()


class ESocialProcedimentoDiagnostico(models.Model):
    _name = "l10n_br.esocial.procedimento.diagnostico"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 27 - Procedimentos Diagnósticos"


class ESocialTreinamento(models.Model):
    _name = "l10n_br.esocial.treinamento"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 28 - Treinamentos e Capacitações"


class ESocialCid(models.Model):
    _name = "l10n_br.esocial.cid"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "CID-10"

    desc_resumida = fields.Char()
