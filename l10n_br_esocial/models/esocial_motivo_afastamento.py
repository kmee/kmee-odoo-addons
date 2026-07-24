# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESocialMotivoAfastamento(models.Model):
    _name = "l10n_br.esocial.motivo.afastamento"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tabela 18 - Motivos de Afastamento"
    _order = "codigo"

    permite_alt_motivo = fields.Char()
    domestico = fields.Char()
    desc_resumida = fields.Char()
    suspende_sal_mensal = fields.Char()
    paga_sal_familia = fields.Char()
    gera_remuneracao = fields.Char()
    mei = fields.Char()
    segurado_especial = fields.Char()
    mpe = fields.Char()
    cod_categ_aplicavel = fields.Text()
