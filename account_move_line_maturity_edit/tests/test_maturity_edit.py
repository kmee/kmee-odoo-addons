from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

GROUP = "account_move_line_maturity_edit.group_edit_posted_maturity"


@tagged("post_install", "-at_install")
class TestMaturityEdit(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        Acc = env["account.account"]
        cls.payable = Acc.create(
            {"name": "AP t", "code": "TMP1", "account_type": "liability_payable", "reconcile": True}
        )
        cls.receivable = Acc.create(
            {"name": "AR t", "code": "TMR1", "account_type": "asset_receivable", "reconcile": True}
        )
        cls.expense = Acc.create({"name": "EXP t", "code": "TMX1", "account_type": "expense"})
        cls.journal = env["account.journal"].create({"name": "Misc t", "code": "TMJ", "type": "general"})
        cls.partner = env["res.partner"].create({"name": "Partner t"})
        # Users: manager (has the group through implied_ids) and plain accountant
        cls.manager = env["res.users"].create(
            {
                "name": "Mgr t", "login": "mgr_t",
                "groups_id": [Command.set([env.ref("base.group_user").id, env.ref("account.group_account_manager").id])],
            }
        )
        cls.accountant = env["res.users"].create(
            {
                "name": "Acc t", "login": "acc_t",
                "groups_id": [Command.set([env.ref("base.group_user").id, env.ref("account.group_account_user").id])],
            }
        )

    def _move(self, post=True):
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.journal.id,
                "date": "2026-11-01",
                "line_ids": [
                    Command.create({"name": "exp", "account_id": self.expense.id, "debit": 100.0}),
                    Command.create(
                        {"name": "ap", "account_id": self.payable.id, "partner_id": self.partner.id,
                         "credit": 100.0, "date_maturity": "2026-11-20"}
                    ),
                ],
            }
        )
        if post:
            move.action_post()
        return move

    def _ui_write(self, line, date, user=None):
        """Write as a user edit (guard opted in) with a non-superuser."""
        user = user or self.manager
        return line.with_user(user).with_context(maturity_edit_check=True).write(
            {"date_maturity": date}
        )

    def _line(self, move, account):
        return move.line_ids.filtered(lambda line: line.account_id == account)

    def test_action_context_has_no_view_no_maturity(self):
        action = self.env.ref("account.action_move_journal_line")
        self.assertNotIn("view_no_maturity", action.context)
        self.assertEqual(
            self.env["account.journal"]
            .browse(self.journal.id)
            .with_context(default_journal_id=self.journal.id)
            ._get_move_action_context()
            .get("view_no_maturity"),
            None,
        )
        self.assertIn("search_default_posted", action.context)
        self.assertIn("default_move_type", action.context)

    def test_journal_items_view_loads(self):
        arch = self.env["account.move.line"].get_view(
            self.env.ref("account.view_move_line_tree").id
        )["arch"]
        self.assertIn("date_maturity", arch)

    def test_draft_entry_edit(self):
        move = self._move(post=False)
        line = self._line(move, self.payable)
        line.write({"date_maturity": "2026-12-05"})
        self.assertEqual(line.date_maturity, fields.Date.to_date("2026-12-05"))
        exp = self._line(move, self.expense)
        exp.write({"date_maturity": "2026-12-05"})  # draft: no restriction

    def test_posted_payable_editable_core_allows(self):
        """Core (hash/lock date) does not block date_maturity on a posted line."""
        move = self._move()
        self.assertEqual(move.state, "posted")
        line = self._line(move, self.payable)
        self._ui_write(line, "2026-12-05")
        self.assertEqual(line.date_maturity, fields.Date.to_date("2026-12-05"))

    def test_posted_with_hash_and_lock_date(self):
        self.journal.restrict_mode_hash_table = True
        move = self._move()
        # Lock the period after posting (SQL: the lock validation needs
        # reconciled bank statements, irrelevant here).
        self.env.cr.execute(
            "UPDATE res_company SET fiscalyear_lock_date = %s WHERE id = %s",
            ("2026-11-30", self.env.company.id),
        )
        self.env.company.invalidate_recordset()
        self.assertTrue(self.env.company.fiscalyear_lock_date)
        line = self._line(move, self.payable)
        self._ui_write(line, "2026-12-06")
        self.assertEqual(line.date_maturity, fields.Date.to_date("2026-12-06"))

    def test_posted_non_payable_blocked(self):
        move = self._move()
        with self.assertRaises(UserError):
            self._ui_write(self._line(move, self.expense), "2026-12-05")

    def test_posted_reconciled_blocked(self):
        move = self._move()
        line = self._line(move, self.payable)
        pay = self.env["account.move"].create(
            {
                "move_type": "entry", "journal_id": self.journal.id, "date": "2026-11-02",
                "line_ids": [
                    Command.create({"name": "p1", "account_id": self.payable.id, "partner_id": self.partner.id, "debit": 100.0}),
                    Command.create({"name": "p2", "account_id": self.expense.id, "credit": 100.0}),
                ],
            }
        )
        pay.action_post()
        (line | self._line(pay, self.payable)).reconcile()
        self.assertTrue(line.reconciled)
        with self.assertRaises(UserError):
            self._ui_write(line, "2026-12-05")

    def test_posted_requires_group(self):
        move = self._move()
        line = self._line(move, self.payable)
        self.assertFalse(self.accountant.has_group(GROUP))
        self.assertTrue(self.manager.has_group(GROUP))
        with self.assertRaises(UserError):
            self._ui_write(line, "2026-12-05", self.accountant)
        self._ui_write(line, "2026-12-07", self.manager)
        self.assertEqual(line.date_maturity, fields.Date.to_date("2026-12-07"))

    def test_draft_without_group_allowed(self):
        move = self._move(post=False)
        line = self._line(move, self.payable)
        line.with_user(self.accountant).write({"date_maturity": "2026-12-08"})
        self.assertEqual(line.date_maturity, fields.Date.to_date("2026-12-08"))

    def test_line_in_payment_order_blocked(self):
        move = self._move()
        line = self._line(move, self.payable)
        mode = self.env["account.payment.mode"].create(
            {
                "name": "Mode t", "company_id": self.env.company.id,
                "bank_account_link": "variable", "payment_method_id": self.env.ref("account.account_payment_method_manual_out").id,
                "payment_order_ok": True,
            }
        )
        order = self.env["account.payment.order"].create(
            {"payment_mode_id": mode.id, "payment_type": "outbound", "journal_id": self.journal.id}
        )
        self.env["account.payment.line"].create(
            {
                "order_id": order.id, "partner_id": self.partner.id, "move_line_id": line.id,
                "amount_currency": 100.0, "currency_id": self.env.company.currency_id.id,
                "communication": "x",
            }
        )
        with self.assertRaises(UserError):
            self._ui_write(line, "2026-12-05")
        # Internal flows (e.g. CNAB change-due-date instruction) write without
        # the opt-in key and must keep working.
        line.with_user(self.manager).write({"date_maturity": "2026-12-09"})
        self.assertEqual(line.date_maturity, fields.Date.to_date("2026-12-09"))
        order.action_cancel()
        self._ui_write(line, "2026-12-05")
        self.assertEqual(line.date_maturity, fields.Date.to_date("2026-12-05"))

    def test_web_save_is_guarded(self):
        move = self._move()
        line = self._line(move, self.expense)
        with self.assertRaises(UserError):
            line.with_user(self.manager).web_save(
                {"date_maturity": "2026-12-05"}, {"id": {}}
            )
        ap = self._line(move, self.payable)
        with self.assertRaises(UserError):
            ap.with_user(self.accountant).web_save(
                {"date_maturity": "2026-12-05"}, {"id": {}}
            )
        ap.with_user(self.manager).web_save({"date_maturity": "2026-12-05"}, {"id": {}})
        self.assertEqual(ap.date_maturity, fields.Date.to_date("2026-12-05"))

    def _logs(self, move):
        return self.env["mail.message"].search(
            [
                ("model", "=", "account.move"),
                ("res_id", "=", move.id),
                ("body", "ilike", "Due date of journal item"),
            ]
        )

    def test_posted_change_is_logged_in_chatter(self):
        move = self._move()
        ap = self._line(move, self.payable)
        self.assertFalse(self._logs(move))
        ap.with_user(self.manager).web_save({"date_maturity": "2026-12-05"}, {"id": {}})
        log = self._logs(move)
        self.assertEqual(len(log), 1)
        self.assertIn("2026-11-20", log.body)
        self.assertIn("2026-12-05", log.body)

    def test_internal_write_is_not_logged(self):
        move = self._move()
        self._line(move, self.payable).write({"date_maturity": "2026-12-05"})
        self.assertFalse(self._logs(move))

    def test_internal_write_without_key_unguarded(self):
        move = self._move()
        self._line(move, self.expense).with_user(self.accountant).write(
            {"date_maturity": "2026-12-05"}
        )

    def test_can_edit_flag_and_view(self):
        line = self._line(self._move(), self.payable)
        self.assertTrue(line.with_user(self.manager).can_edit_posted_maturity)
        self.assertFalse(line.with_user(self.accountant).can_edit_posted_maturity)
        arch = (
            self.env["account.move.line"]
            .with_user(self.accountant)
            .get_view(self.env.ref("account.view_move_line_tree").id)["arch"]
        )
        self.assertIn("can_edit_posted_maturity", arch)
