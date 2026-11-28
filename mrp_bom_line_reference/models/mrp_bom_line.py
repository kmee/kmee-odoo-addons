# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    reference = fields.Text(
        help="Reference designators of this component on the assembly, "
        "e.g. R1, R2, C3.",
    )
    manufacturer_id = fields.Many2one(
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

    @api.constrains("product_qty")
    def _check_product_qty_not_zero(self):
        for line in self:
            if line.product_qty == 0:
                raise ValidationError(
                    _("Bill of materials lines cannot have zero quantity.")
                )
