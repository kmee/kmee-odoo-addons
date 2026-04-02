# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentTermManualMixin(models.AbstractModel):
    _name = "account.payment.term.manual.mixin"
    _description = "Manual Payment Term Mixin"

    manual_payment_term_id = fields.Many2one(
        comodel_name="account.payment.term.manual",
        string="Manual Payment Term",
        copy=False,
    )

    manual_payment_term_line_ids = fields.One2many(
        comodel_name="account.payment.term.line.manual",
        related="manual_payment_term_id.line_ids",
        string="Manual Payment Term Lines",
    )

    has_manual_lines = fields.Boolean(
        related="manual_payment_term_id.has_manual_lines",
    )

    def _update_manual_payment_term_id(self, term_id):
        """Check if invoice term has changed and replace manual term if needed."""
        if self.manual_payment_term_id.mapped("origin_term_id") == term_id:
            # Do nothing if manual term is already based on current term_id
            return

        self = self.with_context(skip_manual_term_onchange=True)

        # THIS SECTION IS ORDER SENSITIVE!
        new_manual_term = term_id.copy_data()[0]
        new_manual_term["origin_term_id"] = term_id.id
        new_manual_term["active"] = False
        new_manual_term["note"] = ""
        # Split creation for term and term.lines
        new_line_ids = new_manual_term.pop("line_ids")
        new_manual_term["line_ids"] = False

        # DO NOT MOVE THIS UNLINK
        self.manual_payment_term_id.line_ids.unlink()
        self.manual_payment_term_id.unlink()
        # DO NOT MOVE THIS CREATE
        manual_term_id = self.manual_payment_term_id.create(new_manual_term)

        # In Odoo 18, copy_data returns line_ids as Command tuples
        line_vals_list = []
        for line_cmd in new_line_ids:
            if isinstance(line_cmd, (list, tuple)):
                # Command.create format: (0, 0, vals)
                if line_cmd[0] == 0:
                    vals = dict(line_cmd[2])
                    vals["manual_payment_id"] = manual_term_id.id
                    vals.pop("payment_id", None)
                    line_vals_list.append(vals)
            elif isinstance(line_cmd, dict):
                vals = dict(line_cmd)
                vals["manual_payment_id"] = manual_term_id.id
                vals.pop("payment_id", None)
                line_vals_list.append(vals)

        if line_vals_list:
            manual_term_id.line_ids = manual_term_id.line_ids.create(line_vals_list)

        self.with_context(
            skip_manual_term_onchange=True
        ).manual_payment_term_id = manual_term_id
