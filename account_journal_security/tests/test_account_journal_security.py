# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountJournalSecurity(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env_su = cls.env(su=True)
        cls.sale_journal = cls.company_data["default_journal_sale"]
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.misc_journal = cls.company_data["default_journal_misc"]

        cls.invoice = cls.init_invoice("out_invoice", products=cls.product_a, post=True)
        cls.payment = cls.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": cls.partner_a.id,
                "amount": 100.0,
                "journal_id": cls.bank_journal.id,
            }
        )
        cls.payment.action_post()
        cls.st_line = cls.env["account.bank.statement.line"].create(
            {
                "journal_id": cls.bank_journal.id,
                "date": "2026-01-01",
                "payment_ref": "statement line",
                "amount": 50.0,
            }
        )
        cls.invoice_lines = cls.invoice.line_ids
        cls.bank_records = (
            cls.bank_journal,
            cls.payment,
            cls.payment.move_id,
            cls.st_line,
            cls.st_line.move_id,
        )

        cls.group_billing = env_su["res.groups"].create({"name": "Billing team"})
        cls.group_treasury = env_su["res.groups"].create({"name": "Treasury team"})
        user_values = {
            "company_id": cls.company.id,
            "company_ids": [Command.set(cls.company.ids)],
        }
        cls.billing_user = new_test_user(
            env_su,
            "billing_user",
            groups="account.group_account_invoice",
            **user_values,
        )
        cls.billing_user.groups_id = [Command.link(cls.group_billing.id)]
        cls.treasury_user = new_test_user(
            env_su,
            "treasury_user",
            groups="account.group_account_invoice",
            **user_values,
        )
        cls.treasury_user.groups_id = [Command.link(cls.group_treasury.id)]
        cls.manager_user = new_test_user(
            env_su,
            "manager_user",
            groups="account.group_account_manager",
            **user_values,
        )

        journals = env_su["account.journal"].search(
            [("company_id", "=", cls.company.id)]
        )
        journals.filtered(
            lambda j: j.type == "sale"
        ).allowed_group_ids = cls.group_billing
        journals.filtered(
            lambda j: j.type == "bank"
        ).allowed_group_ids = cls.group_treasury

    def _visible(self, user, records):
        return (
            self.env[records._name].with_user(user).search([("id", "in", records.ids)])
        )

    def _assert_sees_sale(self, user, visible):
        invoice_lines = self.invoice_lines
        report = self.env["account.invoice.report"].with_user(user)
        self.assertEqual(bool(self._visible(user, self.sale_journal)), visible)
        self.assertEqual(bool(self._visible(user, self.invoice)), visible)
        self.assertEqual(
            self._visible(user, invoice_lines),
            invoice_lines if visible else invoice_lines.browse(),
        )
        self.assertEqual(
            bool(report.search_count([("move_id", "=", self.invoice.id)])), visible
        )

    def _assert_sees_bank(self, user, visible):
        for record in self.bank_records:
            self.assertEqual(bool(self._visible(user, record)), visible, record)

    def test_unrestricted_journal_visible_to_all(self):
        for user in (self.billing_user, self.treasury_user, self.manager_user):
            self.assertEqual(self._visible(user, self.misc_journal), self.misc_journal)

    def test_restricted_journal_visibility(self):
        self._assert_sees_sale(self.billing_user, True)
        self._assert_sees_bank(self.billing_user, False)
        self._assert_sees_sale(self.treasury_user, False)
        self._assert_sees_bank(self.treasury_user, True)
        with self.assertRaises(AccessError):
            self.invoice.with_user(self.treasury_user).read(["name"])

    def test_accounting_manager_outside_groups(self):
        self._assert_sees_sale(self.manager_user, False)
        self._assert_sees_bank(self.manager_user, False)

    def test_create_in_allowed_journal_only(self):
        Journal = self.env["account.journal"].sudo()
        group_other = Journal.env["res.groups"].create({"name": "Other team"})
        hidden_sale, hidden_bank = Journal.create(
            [
                {
                    "name": f"Hidden {journal_type}",
                    "code": f"H{journal_type[:3].upper()}",
                    "type": journal_type,
                    "sequence": 0,
                    "company_id": self.company.id,
                    "allowed_group_ids": group_other.ids,
                }
                for journal_type in ("sale", "bank")
            ]
        )
        values = {
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "invoice_line_ids": [
                Command.create({"product_id": self.product_a.id, "price_unit": 10})
            ],
        }
        invoice = self.env["account.move"].with_user(self.billing_user).create(values)
        self.assertEqual(invoice.journal_id, self.sale_journal)
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")

        payment = (
            self.env["account.payment"]
            .with_user(self.treasury_user)
            .create({"payment_type": "inbound", "partner_type": "customer"})
        )
        self.assertNotEqual(payment.journal_id, hidden_bank)

        Move = self.env["account.move"].with_user(self.treasury_user)
        with self.assertRaises(AccessError):
            Move.create(dict(values, journal_id=hidden_sale.id))
        with self.assertRaisesRegex(UserError, "Allowed Groups"):
            Move.create(values)

    def test_changes_apply_immediately(self):
        user = self.billing_user
        bank_journal = self.bank_journal.sudo()
        bank_journal.allowed_group_ids |= self.group_billing
        self._assert_sees_bank(user, True)
        bank_journal.allowed_group_ids -= self.group_billing
        self._assert_sees_bank(user, False)

        user.sudo().groups_id = [Command.link(self.group_treasury.id)]
        self._assert_sees_bank(user, True)
        user.sudo().groups_id = [Command.unlink(self.group_treasury.id)]
        self._assert_sees_bank(user, False)

        self.group_treasury.sudo().users = [Command.link(user.id)]
        self._assert_sees_bank(user, True)

    def test_multi_company_not_regressed(self):
        env_su = self.env(su=True)
        other_company = env_su["res.company"].create({"name": "Other company"})
        other_journal = env_su["account.journal"].create(
            {
                "name": "Other misc",
                "code": "OMISC",
                "type": "general",
                "company_id": other_company.id,
            }
        )
        self.assertFalse(self._visible(self.billing_user, other_journal))
        other_journal.allowed_group_ids = self.group_billing
        self.assertFalse(self._visible(self.billing_user, other_journal))
