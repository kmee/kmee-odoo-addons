# Copyright (C) 2025 KMEE Informatica LTDA - Luis Felipe Miléo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from odoo.addons.l10n_br_fiscal.constants.fiscal import TAX_DOMAIN

from ..constants import FISCAL_FIELD, FISCAL_FIELD_TAX_DOMAIN_MAP


class AccountMoveTemplateItem(models.Model):
    _name = "l10n_br.account.move.template.item"
    _description = "Double Entry Accounting Template Item"
    _order = "sequence, id"

    template_id = fields.Many2one(
        comodel_name="l10n_br.account.move.template",
        string="Template",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(
        default=10,
    )
    fiscal_field = fields.Selection(
        selection=FISCAL_FIELD,
        required=True,
    )
    tax_domain = fields.Selection(
        selection=TAX_DOMAIN,
    )
    account_debit_id = fields.Many2one(
        comodel_name="account.account",
        string="Debit Account",
        company_dependent=True,
    )
    account_credit_id = fields.Many2one(
        comodel_name="account.account",
        string="Credit Account",
        company_dependent=True,
    )
    require_tax_credit = fields.Boolean(
        help="When checked, this item only generates entries if the fiscal line "
        "has tax credit rights (based on CST codes or credit classification).",
    )

    @api.onchange("fiscal_field")
    def _onchange_fiscal_field(self):
        if self.fiscal_field:
            self.tax_domain = FISCAL_FIELD_TAX_DOMAIN_MAP.get(self.fiscal_field)
