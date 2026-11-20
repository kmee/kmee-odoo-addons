# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseRfqRoundResponse(models.Model):
    _inherit = "purchase.rfq.round.response"

    source = fields.Selection(
        selection_add=[("portal", "Portal")],
        ondelete={"portal": "set default"},
    )
