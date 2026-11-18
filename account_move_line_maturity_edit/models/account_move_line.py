from odoo import _, api, fields, models
from odoo.exceptions import UserError

MATURITY_ACCOUNT_TYPES = ("asset_receivable", "liability_payable")
GROUP = "account_move_line_maturity_edit.group_edit_posted_maturity"


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    can_edit_posted_maturity = fields.Boolean(
        compute="_compute_can_edit_posted_maturity",
        help="Technical: the current user may edit the due date of posted lines.",
    )

    @api.depends_context("uid")
    def _compute_can_edit_posted_maturity(self):
        allowed = self.env.su or self.env.user.has_group(GROUP)
        for line in self:
            line.can_edit_posted_maturity = allowed

    def web_save(self, vals, specification, next_id=None):
        # Saves coming from the web client are user edits: opt in to the
        # due date guard (internal flows call write() directly).
        return super(
            AccountMoveLine, self.with_context(maturity_edit_check=True)
        ).web_save(vals, specification, next_id=next_id)

    def write(self, vals):
        if (
            "date_maturity" in vals
            and self.env.context.get("maturity_edit_check")
            and not self.env.su
        ):
            self._check_date_maturity_edit(vals["date_maturity"])
            changes = self._maturity_changes(vals["date_maturity"])
            res = super().write(vals)
            self._maturity_post_changes(changes)
            return res
        return super().write(vals)

    def _maturity_changes(self, new_value):
        """Posted lines whose due date will change: (line, old, new)."""
        new_date = fields.Date.to_date(new_value)
        return [
            (line, line.date_maturity, new_date)
            for line in self
            if line.parent_state == "posted" and line.date_maturity != new_date
        ]

    def _maturity_post_changes(self, changes):
        # Audit trail: leave the old and new due date in the move chatter.
        for line, old, new in changes:
            user = self.env.user
            line.move_id.sudo().message_post(
                author_id=user.partner_id.id,
                email_from=user.email_formatted or user.login,
                body=_(
                    "Due date of journal item %(item)s changed from %(old)s "
                    "to %(new)s.",
                    item=line.name or line.account_id.display_name,
                    old=old or _("(empty)"),
                    new=new or _("(empty)"),
                )
            )

    def _check_date_maturity_edit(self, new_value):
        new_date = fields.Date.to_date(new_value)
        lines = self.filtered(
            lambda line: line.parent_state == "posted"
            and line.date_maturity != new_date
        )
        if not lines:
            return
        # Lines already in a (non-cancelled) payment order.
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
        invalid = lines.filtered(
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
        if not self.env.user.has_group(GROUP):
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
