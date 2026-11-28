# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    production_id = fields.Many2one(
        comodel_name="mrp.production",
        string="Manufacturing Order",
        index=True,
    )
    production_date_finished = fields.Datetime(
        related="production_id.date_finished",
        string="MO Deadline",
    )
    schedule_date = fields.Date(string="Scheduled Date")
    justificativa = fields.Text(string="Justification")
    default_code = fields.Char(
        related="product_id.default_code",
        store=True,
    )
    manufacturer_pref = fields.Char(
        related="product_id.manufacturer_pref",
        string="Manufacturer Part Number",
    )
