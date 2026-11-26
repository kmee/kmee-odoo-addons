# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models

INFO_HELP = "For information only."


class ProductTemplate(models.Model):
    _inherit = "product.template"

    stock = fields.Char(string="Stock (Main)", help=INFO_HELP)
    posx = fields.Char(string="Aisle (Main)", help=INFO_HELP)
    posy = fields.Char(string="Shelf (Main)", help=INFO_HELP)
    posz = fields.Char(string="Height (Main)", help=INFO_HELP)
    box = fields.Char(string="Box (Main)", help=INFO_HELP)
    caixa = fields.Char(string="Carton (Main)", help=INFO_HELP)
    nivel = fields.Char(string="Level (Main)", help=INFO_HELP)
    second_stock = fields.Char(string="Stock (Alternative)", help=INFO_HELP)
    second_posx = fields.Char(string="Aisle (Alternative)", help=INFO_HELP)
    second_posy = fields.Char(string="Shelf (Alternative)", help=INFO_HELP)
    second_posz = fields.Char(string="Height (Alternative)", help=INFO_HELP)
    second_box = fields.Char(string="Box (Alternative)", help=INFO_HELP)
    second_caixa = fields.Char(string="Carton (Alternative)", help=INFO_HELP)
    second_nivel = fields.Char(string="Level (Alternative)", help=INFO_HELP)
