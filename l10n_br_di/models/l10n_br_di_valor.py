# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from .l10n_br_di_declaracao import D2


class L10nBrDiValor(models.Model):

    _name = "l10n_br_di.valor"
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
    valor_moeda_negociada = fields.Monetary(currency_field="moeda_negociada_id")
    valor = fields.Monetary(currency_field="moeda_empresa_id")

    moeda_negociada_id = fields.Many2one("res.currency")
    moeda_empresa_id = fields.Many2one("res.currency")

    moeda_taxa = fields.Float()

    def _importa_declaracao(self, acrescimo, deducao):
        acrescimo_deducao = []

        if acrescimo:
            # trade_currency_id = self.env["res.currency"].search(
            #     [("siscomex_code", "=", acrescimo.moeda_negociada_codigo)],
            #     limit=1,
            # )
            amount_reais = int(acrescimo.valor_reais) / D2
            amount_currency = int(acrescimo.valor_moeda_negociada) / D2
            if amount_currency and amount_reais:
                amount_reais / amount_currency
            else:
                pass

            acrescimo_deducao.append(
                {
                    "codigo": acrescimo.codigo_acrescimo,
                    "denominacao": acrescimo.denominacao,
                    "moeda_negociada_codigo": acrescimo.moeda_negociada_codigo,
                    "moeda_negociada_nome": acrescimo.moeda_negociada_nome,
                    "valor": amount_reais,
                    "valor_moeda_negociada": amount_currency,
                    # "currency_rate": currency_rate,
                    # "moeda_negociada_id": trade_currency_id.id
                    # if trade_currency_id
                    # else False,
                }
            )

        if deducao:
            # trade_currency_id = self.env["res.currency"].search(
            #     [("siscomex_code", "=", deducao.moeda_negociada_codigo)],
            #     limit=1,
            # )
            amount_reais = int(deducao.valor_reais) / D2 * -1
            amount_currency = int(deducao.valor_moeda_negociada) / D2 * -1
            if amount_currency and amount_reais:
                amount_reais / amount_currency
            else:
                pass

            acrescimo_deducao.append(
                {
                    "codigo": deducao.codigo_deducao,
                    "denominacao": deducao.denominacao,
                    "moeda_negociada_codigo": deducao.moeda_negociada_codigo,
                    "moeda_negociada_nome": deducao.moeda_negociada_nome,
                    "valor": amount_reais,
                    "valor_moeda_negociada": amount_currency,
                    # if trade_currency_id
                    # else False,
                }
            )

        return acrescimo_deducao
