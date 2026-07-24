# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESocialAgenteNocivo(models.Model):
    _name = "l10n_br.esocial.agente.nocivo"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 22 - Agentes Nocivos"

    tipo = fields.Char()


class ESocialAposentadoriaEspecial(models.Model):
    _name = "l10n_br.esocial.aposentadoria.especial"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 23 - Aposentadoria Especial INSS"

    tempo_contribuicao = fields.Char()
    aliquota = fields.Char()


class ESocialProcedimentoDiagnostico(models.Model):
    _name = "l10n_br.esocial.procedimento.diagnostico"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 27 - Procedimentos Diagnósticos"


class ESocialTreinamento(models.Model):
    _name = "l10n_br.esocial.treinamento"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 29 - Treinamentos e Capacitações"


class ESocialCid(models.Model):
    _name = "l10n_br.esocial.cid"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 60 - CID"

    desc_resumida = fields.Char()
