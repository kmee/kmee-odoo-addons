# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    procurement_group_id = fields.Many2one(
        comodel_name="procurement.group",
        string="Procurement Group",
        copy=False,
    )
    production_origins = fields.Char(compute="_compute_production_origins")

    @api.depends("line_ids.production_id")
    def _compute_production_origins(self):
        for requisition in self:
            requisition.production_origins = ", ".join(
                requisition.sudo().line_ids.production_id.mapped("display_name")
            )
