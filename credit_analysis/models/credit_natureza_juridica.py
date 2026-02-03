# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CreditNaturezaJuridica(models.Model):
    _name = "credit.natureza.juridica"
    _description = "Natureza Juridica"
    _order = "code"

    code = fields.Char(
        string="Codigo",
        index="btree",
    )
    name = fields.Char(
        string="Descricao",
        required=True,
    )
    active = fields.Boolean(
        default=True,
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "O codigo deve ser unico!"),
    ]

    def name_get(self):
        result = []
        for record in self:
            if record.code:
                name = f"{record.code} - {record.name}"
            else:
                name = record.name
            result.append((record.id, name))
        return result
