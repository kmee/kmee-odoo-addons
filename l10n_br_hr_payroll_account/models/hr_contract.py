# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    # Na 17.0 o diario do holerite e related ao do contrato (payroll_account).
    # O default vai aqui: o contrato nasce no diario de folha (FOPAG) em vez do
    # primeiro diario `general` da base (ver account.journal._l10n_br_payroll_journal).
    journal_id = fields.Many2one(
        default=lambda self: self.env["account.journal"]._l10n_br_payroll_journal()
    )
