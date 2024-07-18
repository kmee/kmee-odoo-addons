# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from .l10n_br_di_declaracao import D5


class L10nBrDiMercadoria(models.Model):

    _name = "l10n_br_di.mercadoria"
    _description = "Declaração de Importação Mercadoria"

    declaracao_id = fields.Many2one(
        "l10n_br_di.declaracao",
        related="adicao_id.declaracao_id",
    )

    adicao_id = fields.Many2one(
        "l10n_br_di.adicao", string="Adição", required=True, ondelete="cascade"
    )

    descricao_mercadoria = fields.Char()
    numero_sequencial_item = fields.Char()
    quantidade = fields.Char()
    unidade_medida = fields.Char()
    valor_unitario = fields.Char()

    def _importa_declaracao(self, mercadoria):
        return {
            "numero_sequencial_item": int(mercadoria.numero_sequencial_item),
            "descricao_mercadoria": mercadoria.descricao_mercadoria,
            "quantidade": int(mercadoria.quantidade) / D5,
            "unidade_medida": mercadoria.unidade_medida,
            "valor_unitario": int(mercadoria.valor_unitario) / D5,
        }
