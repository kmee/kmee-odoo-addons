# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from .l10n_br_di_declaracao import D5, D7


class L10nBrDiMercadoria(models.Model):

    _name = "l10n_br_di.mercadoria"
    _description = "Declaração de Importação Mercadoria"

    # @api.depends("product_qty", "price_unit", "currency_rate", "import_addition_id")
    def _compute_totals(self):
        for line in self:
            line.price_unit = line.valor_unitario * line.taxa_cambio_venda
            line.amount_subtotal = line.quantidade * line.valor_unitario
            line.amount_subtotal_brl = line.quantidade * line.price_unit

            line.unit_addition_deduction = (
                line.adicao_id.amount_add_ded_brl
                * line.amount_subtotal_brl
                / line.adicao_id.condicao_venda_valor_reais
            ) / line.quantidade

            line.amount_other = (
                line.adicao_id.valor_outros
                * line.amount_subtotal_brl
                / line.adicao_id.condicao_venda_valor_reais
            )

            line.amount_afrmm = line.amount_other - (
                line.adicao_id.valor_taxa_siscomex
                * line.amount_subtotal_brl
                / line.adicao_id.condicao_venda_valor_reais
            )

            line.final_price_unit = line.price_unit + line.unit_addition_deduction

            line.amount_total = line.final_price_unit * line.quantidade

    declaracao_id = fields.Many2one(
        "l10n_br_di.declaracao",
        related="adicao_id.declaracao_id",
    )

    currency_id = fields.Many2one(
        "res.currency",
        related="declaracao_id.currency_id",
    )

    adicao_id = fields.Many2one(
        "l10n_br_di.adicao", string="Adição", required=True, ondelete="cascade"
    )

    moeda_venda_id = fields.Many2one(
        "res.currency",
        related="adicao_id.moeda_venda_id",
    )

    taxa_cambio_venda = fields.Float(
        digits=(12, 8),
        related="adicao_id.taxa_cambio_venda",
    )

    numero_sequencial_item = fields.Integer(string="Seq.")
    descricao_mercadoria = fields.Char(string="Descrição")
    quantidade = fields.Float(string="Qty")
    unidade_medida = fields.Char(string="Uom")
    valor_unitario = fields.Float(
        string="vUnMoeda",
        digits=(12, 8),
    )

    # Campos do produto para mapeamento do produto:

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
    )

    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")

    price_unit = fields.Float(
        string="vUnBRL",
        digits=(12, 8),
    )

    amount_subtotal = fields.Float(
        string="Subtotal (Moeda)",
        digits=(12, 8),
    )
    amount_subtotal_brl = fields.Float()

    unit_addition_deduction = fields.Monetary(
        string="+/-",
        digits=(12, 8),
        help="Equals to the sum of all di_valor_ids.valor divided by the sum of "
        "di_mercadoria_ids.quantidade",
    )

    final_price_unit = fields.Float()

    amount_other = fields.Float()

    amount_total = fields.Float()

    amount_afrmm = fields.Float()

    def _importa_declaracao(self, mercadoria):
        vals = {
            "numero_sequencial_item": int(mercadoria.numero_sequencial_item),
            "descricao_mercadoria": mercadoria.descricao_mercadoria,
            "quantidade": int(mercadoria.quantidade) / D5,
            "unidade_medida": mercadoria.unidade_medida,
            "valor_unitario": int(mercadoria.valor_unitario) / D7,
        }
        self._match_product_unit(
            vals,
            mercadoria.descricao_mercadoria,
            mercadoria.unidade_medida,
        )
        return vals

    def _match_product_unit(self, vals, descricao_mercadoria, unidade_medida):
        """
        Método para buscar o produto correspondente a mercadoria,
        pesquisa nas útimas DIs criadas do mesmo produto e tenta preencher
        automaticamente os campos product_id e uom_id.
        """
        # TODO: Implementar a busca do produto
