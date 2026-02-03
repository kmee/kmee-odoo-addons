# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CreditCnae(models.Model):
    _name = "credit.cnae"
    _description = "CNAE - Classificacao Nacional de Atividades Economicas"
    _order = "code"

    code = fields.Char(
        string="Codigo",
        required=True,
        index="btree",
    )
    name = fields.Char(
        string="Descricao",
        required=True,
    )
    description = fields.Text(
        string="Descricao Detalhada",
    )
    active = fields.Boolean(
        default=True,
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "O codigo CNAE deve ser unico!"),
    ]

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.code} - {record.name}"
            result.append((record.id, name))
        return result
