from odoo import _, models
from odoo.exceptions import UserError

MATURITY_ACCOUNT_TYPES = ("asset_receivable", "liability_payable")


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def write(self, vals):
        if "date_maturity" in vals:
            self._check_date_maturity_edit(vals["date_maturity"])
        return super().write(vals)

    def _check_date_maturity_edit(self, new_value):
        new_date = self.env["account.move.line"]._fields[
            "date_maturity"
        ].convert_to_cache(new_value, self)
        lines = self.filtered(lambda line: line.date_maturity != new_date)
        if not lines:
            return
        # Lines already in a (non-cancelled) payment order: always blocked.
        payment_lines = (
            self.env["account.payment.line"]
            .sudo()
            .search(
                [
                    ("move_line_id", "in", lines.ids),
                    ("order_id.state", "!=", "cancel"),
                ]
            )
        )
        if payment_lines:
            raise UserError(
                _(
                    "You cannot change the due date of the following journal "
                    "items because they are already included in a payment "
                    "order:\n%(lines)s",
                    lines=self._maturity_lines_label(payment_lines.move_line_id),
                )
            )
        posted = lines.filtered(lambda line: line.parent_state == "posted")
        if not posted:
            return
        invalid = posted.filtered(
            lambda line: line.account_id.account_type not in MATURITY_ACCOUNT_TYPES
            or line.reconciled
            or line.display_type in ("line_section", "line_note")
        )
        if invalid:
            raise UserError(
                _(
                    "The due date of a posted entry can only be changed on "
                    "receivable/payable lines that are not reconciled. "
                    "Invalid lines:\n%(lines)s",
                    lines=self._maturity_lines_label(invalid),
                )
            )
        if not self.env.su and not self.env.user.has_group(
            "account_move_line_maturity_edit.group_edit_posted_maturity"
        ):
            raise UserError(
                _(
                    "You are not allowed to change the due date of posted "
                    "entries. Ask an administrator for the group "
                    "'Edit due date of posted journal items'."
                )
            )

    def _maturity_lines_label(self, lines):
        return "\n".join(
            "%s - %s"
            % (
                line.move_id.name or line.move_id.display_name,
                line.name or line.account_id.display_name,
            )
            for line in lines
        )
