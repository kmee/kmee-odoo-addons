# Copyright (C) 2025 KMEE Informatica LTDA - Luis Felipe Miléo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FiscalOperation(models.Model):
    _inherit = "l10n_br_fiscal.operation"

    account_move_template_id = fields.Many2one(
        comodel_name="l10n_br.account.move.template",
        string="Accounting Template",
        company_dependent=True,
    )
