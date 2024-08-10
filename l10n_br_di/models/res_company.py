# Copyright (C) 2024 Luis Felipe Miléo - KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    import_trade_fiscal_operation_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.operation",
        domain=[("state", "=", "approved")],
    )
