# Copyright (C) 2025 KMEE Informatica LTDA - Luis Felipe Miléo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.l10n_br_fiscal.constants.fiscal import FISCAL_IN_OUT_ALL


class AccountMoveTemplate(models.Model):
    _name = "l10n_br.account.move.template"
    _description = "Double Entry Accounting Template"
    _order = "name"

    name = fields.Char(
        required=True,
        translate=True,
    )
    active = fields.Boolean(
        default=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    fiscal_operation_type = fields.Selection(
        selection=FISCAL_IN_OUT_ALL,
    )
    fiscal_operation_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.operation",
        relation="l10n_br_account_move_template_operation_rel",
        column1="template_id",
        column2="operation_id",
        string="Fiscal Operations",
    )
    parent_id = fields.Many2one(
        comodel_name="l10n_br.account.move.template",
        string="Parent Template",
        ondelete="restrict",
    )
    child_ids = fields.One2many(
        comodel_name="l10n_br.account.move.template",
        inverse_name="parent_id",
        string="Child Templates",
    )
    item_ids = fields.One2many(
        comodel_name="l10n_br.account.move.template.item",
        inverse_name="template_id",
        string="Items",
    )

    @api.constrains("parent_id")
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(
                _("Error! You cannot create recursive template hierarchies.")
            )

    def _get_all_items(self):
        """Collect template items from the hierarchy, child items take precedence."""
        self.ensure_one()
        items = self.item_ids
        if self.parent_id:
            parent_items = self.parent_id._get_all_items()
            # Only add parent items whose fiscal_field is not already covered
            covered_fields = set(items.mapped("fiscal_field"))
            items |= parent_items.filtered(
                lambda i: i.fiscal_field not in covered_fields
            )
        return items.sorted("sequence")
