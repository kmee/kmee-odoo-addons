# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountBankStatementLine(models.Model):

    _inherit = "account.bank.statement.line"

    running_balance = fields.Monetary(
        compute="_compute_running_balance",
        store=True,
    )
