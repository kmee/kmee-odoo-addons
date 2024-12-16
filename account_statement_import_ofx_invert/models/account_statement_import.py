# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountStatementImport(models.TransientModel):

    _inherit = "account.statement.import"

    @api.model
    def _prepare_ofx_transaction_line(self, transaction):
        vals = super()._prepare_ofx_transaction_line(transaction)
        journal = self.env["account.journal"].browse(self.env.context.get("journal_id"))
        if journal and journal.reverse_balance_of_entries:
            vals["amount"] = -1 * vals["amount"]
        return vals
