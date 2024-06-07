# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    origin_term_id = fields.Many2one(
        comodel_name="account.payment.term",
        string="Payment Terms",
        required=False,
    )

    has_manual_lines = fields.Boolean(
        help="Technical field to keep track of manual lines",
    )
