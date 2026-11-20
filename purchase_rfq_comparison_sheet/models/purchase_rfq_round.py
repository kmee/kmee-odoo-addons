# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models


class PurchaseRfqRound(models.Model):
    _inherit = "purchase.rfq.round"

    def _get_sheet_columns(self):
        columns = super()._get_sheet_columns()
        notes = columns.pop()
        columns += [
            {
                "key": "payment_term",
                "label": _("Payment Terms"),
                "width": 18,
                "input": True,
                "value": lambda pol: pol.rfq_payment_term_id.name or None,
            },
            {
                "key": "validity",
                "label": _("Valid Until"),
                "width": 12,
                "input": True,
                "value": lambda pol: None,
            },
            {
                "key": "min_qty",
                "label": _("Minimum Qty"),
                "width": 10,
                "input": True,
                "value": lambda pol: None,
            },
            {
                "key": "spec",
                "label": _("Meets Specification (Y/N)"),
                "width": 12,
                "input": True,
                "value": lambda pol: None,
            },
            notes,
        ]
        return columns
