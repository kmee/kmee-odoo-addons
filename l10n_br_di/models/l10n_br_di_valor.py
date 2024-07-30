# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from .l10n_br_di_declaracao import D2


class L10nBrDiValor(models.Model):

    _name = "l10n_br_di.valor"
    _inherit = "l10n_br_di.mixin"
    _description = "Declaração Importação Valores"

    declaracao_id = fields.Many2one(
        "l10n_br_di.declaracao",
        related="adicao_id.declaracao_id",
    )

    adicao_id = fields.Many2one(
        "l10n_br_di.adicao", string="Adição", required=True, ondelete="cascade"
    )

    codigo = fields.Integer()
    denominacao = fields.Char()
    moeda_negociada_codigo = fields.Char()
    moeda_negociada_nome = fields.Char()
    valor_moeda_negociada = fields.Float()
    valor = fields.Float()

    moeda_negociada_id = fields.Many2one("res.currency")
    moeda_empresa_id = fields.Many2one(
        "res.currency", related="declaracao_id.currency_id"
    )

    moeda_taxa = fields.Float()

    def _importa_declaracao(self, acrescimo, deducao):
        acrescimo_deducao = []

        if acrescimo:
            amount_reais = int(acrescimo.valor_reais) / D2
            amount_currency = int(acrescimo.valor_moeda_negociada) / D2

            trade_currency_id = self._s_currency(acrescimo.moeda_negociada_codigo)
            if amount_currency and amount_reais:
                currency_rate = amount_reais / amount_currency
            else:
                currency_rate = False

            acrescimo_deducao.append(
                {
                    "codigo": acrescimo.codigo_acrescimo,
                    "denominacao": acrescimo.denominacao,
                    "moeda_negociada_codigo": acrescimo.moeda_negociada_codigo,
                    "moeda_negociada_nome": acrescimo.moeda_negociada_nome,
                    "valor": amount_reais,
                    "valor_moeda_negociada": amount_currency,
                    "moeda_taxa": currency_rate,
                    "moeda_negociada_id": trade_currency_id.id
                    if trade_currency_id
                    else False,
                }
            )

        if deducao:
            amount_reais = int(deducao.valor_reais) / D2 * -1
            amount_currency = int(deducao.valor_moeda_negociada) / D2 * -1

            trade_currency_id = self._s_currency(deducao.moeda_negociada_codigo)
            if amount_currency and amount_reais:
                currency_rate = amount_reais / amount_currency
            else:
                currency_rate = False

            acrescimo_deducao.append(
                {
                    "codigo": deducao.codigo_deducao,
                    "denominacao": deducao.denominacao,
                    "moeda_negociada_codigo": deducao.moeda_negociada_codigo,
                    "moeda_negociada_nome": deducao.moeda_negociada_nome,
                    "valor": amount_reais,
                    "valor_moeda_negociada": amount_currency,
                    "moeda_taxa": currency_rate,
                    "moeda_negociada_id": trade_currency_id.id
                    if trade_currency_id
                    else False,
                }
            )

        return acrescimo_deducao
