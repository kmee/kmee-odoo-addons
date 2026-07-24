# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESocialMotivoDesligamento(models.Model):
    _name = "l10n_br.esocial.motivo.desligamento"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 19 - Motivos de Desligamento"
    _order = "codigo"

    gera_dae = fields.Char()
    categ_trab_aplicavel = fields.Text()
    gera_ind_cumprimento = fields.Char()
    desc_resumida = fields.Char()
    cod_categ_aplicavel = fields.Text()
    aplic_deslig_baixa_jud = fields.Char()
