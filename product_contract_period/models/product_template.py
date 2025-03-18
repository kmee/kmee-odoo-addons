# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    default_period_qty = fields.Float(
        string="Quantidade Padrão por Período", default=1.0
    )
    default_period_count = fields.Integer(string="Número Padrão de Períodos", default=1)
