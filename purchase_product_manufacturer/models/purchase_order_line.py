# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    manufacturer = fields.Many2one(
        comodel_name="res.partner",
        related="product_id.manufacturer_id",
        string="Manufacturer",
    )
    manufacturer_pname = fields.Char(
        related="product_id.manufacturer_pname",
        string="Manufacturer Product Name",
    )
    manufacturer_pref = fields.Char(
        related="product_id.manufacturer_pref",
        string="Manufacturer Product Code",
    )
    manufacturer_purl = fields.Char(
        related="product_id.manufacturer_purl",
        string="Manufacturer Product URL",
    )
