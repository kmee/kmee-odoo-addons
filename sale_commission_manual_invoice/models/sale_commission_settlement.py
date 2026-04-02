# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Disable automatic invoice generation for commission settlements."""

from odoo import _, fields, models
from odoo.exceptions import UserError


class Settlement(models.Model):
    _inherit = "commission.settlement"

    state = fields.Selection(
        selection_add=[("paid", "Paid")],
        ondelete={"paid": "set default"},
    )

    def action_invoice(self):
        raise UserError(
            _(
                "Automatic invoice generation is disabled. "
                "Create invoices manually and mark settlements as invoiced."
            )
        )

    def action_confirm(self):
        for settlement in self:
            settlement.write({"state": "paid"})
        return True

    def action_mark_invoiced(self):
        for settlement in self:
            settlement.write({"state": "invoiced"})
        return True

    def action_cancel(self):
        for settlement in self:
            settlement.write({"state": "cancel"})
        return True

    def action_except_invoice(self):
        for settlement in self:
            settlement.write({"state": "except_invoice"})
        return True

    def action_settle(self):
        for settlement in self:
            settlement.write({"state": "settled"})
        return True

    def make_invoices(self, journal, product, date=False, grouped=False):
        raise UserError(
            _(
                "Automatic invoice creation is disabled. Handle invoicing manually."
            )
        )
