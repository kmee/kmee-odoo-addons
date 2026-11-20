# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseRfqRoundAward(models.TransientModel):
    _inherit = "purchase.rfq.round.award"

    criterion = fields.Selection(
        selection_add=[("score", "Best score")],
        ondelete={"score": "set default"},
    )

    def _default_criterion(self):
        return "score"
