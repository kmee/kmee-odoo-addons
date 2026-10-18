# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from decimal import Decimal

from odoo import api, models


class AccountStatementImport(models.TransientModel):

    _inherit = "account.statement.import"

    @api.model
    def _check_ofx(self, data_file):
        ofx = super()._check_ofx(data_file)
        journal_id = self.env["account.journal"].browse(
            self.env.context.get("journal_id")
        )
        reverse_balance_of_entries_ofx = journal_id.reverse_balance_of_entries_ofx
        ignore_ofx_balance = journal_id.ignore_ofx_balance
        if ofx and journal_id:
            if ignore_ofx_balance:
                last_statement = self.env["account.bank.statement"].search(
                    [("journal_id", "=", journal_id.id)], limit=1, order="date asc"
                )
                balance = Decimal(last_statement.balance_end_real)
            for transaction in ofx.account.statement.transactions:
                if reverse_balance_of_entries_ofx:
                    if transaction.type == "credit":
                        transaction.type = "debit"
                    elif transaction.type == "debit":
                        transaction.type = "credit"
                    transaction.amount = transaction.amount * (-1)
                else:
                    pass

                if ignore_ofx_balance:
                    balance += transaction.amount

            if ignore_ofx_balance:
                ofx.account.statement.balance = balance
                if not last_statement:
                    ofx.account.statement.balance = False
        return ofx
