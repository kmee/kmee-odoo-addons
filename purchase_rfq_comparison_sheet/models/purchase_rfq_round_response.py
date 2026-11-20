# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseRfqRoundResponse(models.Model):
    _inherit = "purchase.rfq.round.response"

    payment_term_id = fields.Many2one("account.payment.term", string="Payment Terms")
    validity_date = fields.Date(string="Valid Until")
    min_qty = fields.Float(string="Minimum Qty", digits="Product Unit of Measure")
    spec_approved = fields.Boolean(string="Meets Specification")
