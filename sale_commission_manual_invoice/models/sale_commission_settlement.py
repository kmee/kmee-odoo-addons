# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class Settlement(models.Model):
    _inherit = "sale.commission.settlement"

    state = fields.Selection(
        selection=[
            ("settled", "Open"),
            ("paid", "Paid"),
            ("invoiced", "Invoiced"),
            ("cancel", "Canceled"),
            ("except_invoice", "Invoice exception"),
        ],
        string="State",
        readonly=True,
        default="settled",
    )

    def action_invoice(self):
        raise UserError(
            _(
                """Automatic invoice generation is disabled.
                Create invoices manually and mark settlements as invoiced."""
            )
        )

    def action_confirm(self):
        for settlement in self:
            settlement.write({"state": "paid"})

    def action_mark_invoiced(self):
        for settlement in self:
            settlement.write({"state": "invoiced"})

    def action_cancel(self):
        for settlement in self:
            settlement.write({"state": "cancel"})

    def action_except_invoice(self):
        for settlement in self:
            settlement.write({"state": "except_invoice"})

    def action_settle(self):
        for settlement in self:
            settlement.write({"state": "settled"})

    def make_invoices(self, *args, **kwargs):
        raise UserError(
            _("Automatic invoice creation is disabled. Handle invoicing manually.")
        )
