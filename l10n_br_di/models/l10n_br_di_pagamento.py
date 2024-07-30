# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from .l10n_br_di_declaracao import D2, c_data


class L10nBrDiPagamento(models.Model):

    _name = "l10n_br_di.pagamento"
    _description = "Declaração Importação Pagamento"

    declaracao_id = fields.Many2one(
        "l10n_br_di.declaracao", string="Declaração", required=True, ondelete="cascade"
    )

    currency_id = fields.Many2one(
        "res.currency",
        related="declaracao_id.currency_id",
        readonly=True,
    )

    agencia_pagamento = fields.Char()
    banco_pagamento = fields.Char()
    codigo_receita = fields.Char()
    codigo_tipo_pagamento = fields.Char()
    conta_pagamento = fields.Char()
    data_pagamento = fields.Date()
    nome_tipo_pagamento = fields.Char()
    numero_retificacao = fields.Char()
    valor_juros_encargos = fields.Float()
    valor_multa = fields.Float()
    valor_receita = fields.Float()

    def _importa_declaracao(self, pagamento):
        return {
            "agencia_pagamento": pagamento.agencia_pagamento,
            "banco_pagamento": pagamento.banco_pagamento,
            "codigo_receita": pagamento.codigo_receita,
            "codigo_tipo_pagamento": pagamento.codigo_tipo_pagamento,
            "conta_pagamento": pagamento.conta_pagamento,
            "data_pagamento": c_data(pagamento.data_pagamento),
            "nome_tipo_pagamento": pagamento.nome_tipo_pagamento,
            "numero_retificacao": pagamento.numero_retificacao,
            "valor_juros_encargos": int(pagamento.valor_juros_encargos) / D2,
            "valor_multa": int(pagamento.valor_multa) / D2,
            "valor_receita": int(pagamento.valor_receita) / D2,
        }
