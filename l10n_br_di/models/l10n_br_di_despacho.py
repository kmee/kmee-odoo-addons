# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class L10nBrDespacho(models.Model):

    _name = "l10n_br_di.despacho"
    _description = "Declaração de Importação Despacho"

    declaracao_id = fields.Many2one(
        "l10n_br_di.declaracao", string="Declaração", required=True, ondelete="cascade"
    )

    codigo_tipo_documento_despacho = fields.Char()
    nome_documento_despacho = fields.Char()
    numero_documento_despacho = fields.Char()

    def _importa_declaracao(self, despacho):
        return {
            "codigo_tipo_documento_despacho": despacho.codigo_tipo_documento_despacho,
            "nome_documento_despacho": despacho.nome_documento_despacho,
            "numero_documento_despacho": despacho.numero_documento_despacho,
        }
