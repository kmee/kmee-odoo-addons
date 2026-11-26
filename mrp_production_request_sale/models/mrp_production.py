# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    is_sub_mo = fields.Boolean(
        string="Sub-MO",
        readonly=True,
        copy=False,
        help="The order manufactures a component of another manufacturing order.",
    )
