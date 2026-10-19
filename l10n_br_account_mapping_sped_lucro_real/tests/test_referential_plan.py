# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReferentialPlan(TransactionCase):
    """Plano referencial Lucro Real (leiaute 12) carregado pelo modulo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.plan = cls.env.ref(
            "l10n_br_account_mapping_sped_lucro_real.plan_referencial_1_l12"
        )
        cls.accounts = cls.plan.account_ids
        cls.odoo_account = cls.env["account.account"].create(
            {
                "name": "Caixa teste referencial",
                "code": "REFTEST1",
                "account_type": "asset_cash",
                "company_id": cls.env.company.id,
            }
        )

    def _ref(self, code):
        return self.accounts.filtered(lambda account: account.code == code)

    def test_plan_is_a_referential_plan_of_rfb(self):
        """
        Given the module is installed
        When the plan record is read
        Then it is a referential plan with code 1, layout 12, valid
        for every company
        """
        self.assertTrue(self.plan.sped_referential)
        self.assertEqual(self.plan.sped_plan_code, "1")
        self.assertEqual(self.plan.sped_layout_version, "12")
        self.assertFalse(self.plan.company_id)
        self.assertIn("Lucro Real", self.plan.name)

    def test_official_table_is_fully_loaded(self):
        """
        Given the official RFB table
        When the accounts of the plan are counted
        Then 1123 accounts are loaded: 975 analytic and 148 synthetic
        """
        self.assertEqual(self.plan.account_count, 1123)
        self.assertEqual(
            len(self.accounts.filtered(lambda a: a.sped_account_type == "A")), 975
        )
        self.assertEqual(
            len(self.accounts.filtered(lambda a: a.sped_account_type == "S")), 148
        )

    def test_hierarchy_is_consistent(self):
        """
        Given the loaded table
        When parents are followed
        Then the roots are 1, 2 and 3, every parent exists in the plan and
        analytic accounts are never parents
        """
        roots = self.accounts.filtered(lambda a: not a.sped_parent_code)
        self.assertEqual(sorted(roots.mapped("code")), ["1", "2", "3"])
        codes = set(self.accounts.mapped("code"))
        parents = {a.sped_parent_code for a in self.accounts if a.sped_parent_code}
        self.assertFalse(parents - codes)
        analytic = self.accounts.filtered(lambda a: a.sped_account_type == "A")
        self.assertFalse(parents & set(analytic.mapped("code")))

    def test_known_analytic_account_attributes(self):
        """
        Given the official table
        When the account 1.01.01.01.01 is read
        Then it is the analytic 'Caixa Matriz', level 5, nature 1, child of
        1.01.01.01 and valid since 2015
        """
        account = self._ref("1.01.01.01.01")
        self.assertEqual(len(account), 1)
        self.assertEqual(account.name, "Caixa Matriz")
        self.assertEqual(account.sped_account_type, "A")
        self.assertEqual(account.sped_level, 5)
        self.assertEqual(account.sped_nature, "1")
        self.assertEqual(account.sped_parent_code, "1.01.01.01")
        self.assertEqual(account.date_start, fields.Date.to_date("2015-01-01"))
        self.assertFalse(account.date_end)

    def test_known_synthetic_root(self):
        """
        Given the official table
        When the root account 1 is read
        Then it is the synthetic ATIVO at level 1
        """
        root = self._ref("1")
        self.assertEqual(root.name, "ATIVO")
        self.assertEqual(root.sped_account_type, "S")
        self.assertEqual(root.sped_level, 1)

    def test_i051_line_uses_plan_code_and_loaded_account(self):
        """
        Given an Odoo account mapped to 1.01.01.01.01 and the company using
        this plan
        When the I051 data of the account is requested
        Then COD_PLAN_REF is 1 and COD_CTA_REF is 1.01.01.01.01
        """
        self._ref("1.01.01.01.01").account_ids = [(4, self.odoo_account.id)]
        self.env.company.l10n_br_sped_referential_plan_id = self.plan
        self.assertEqual(
            self.odoo_account.l10n_br_sped_referential_line(),
            {"COD_PLAN_REF": "1", "COD_CTA_REF": "1.01.01.01.01"},
        )

    def test_unmapped_account_has_no_i051(self):
        """
        Given a company using the plan and an account not mapped
        When the I051 data is requested
        Then it is empty, and the plan lists the account as unmapped
        """
        self.env.company.l10n_br_sped_referential_plan_id = self.plan
        self.assertEqual(self.odoo_account.l10n_br_sped_referential_line(), {})
        self.assertEqual(
            self.plan.unmapped_odoo_accounts(self.odoo_account), self.odoo_account
        )

    def test_validity_date_limits_new_accounts(self):
        """
        Given an account of the table that is valid only since 2025-01-01
        When the Odoo account mapped to it is resolved before and after that date
        Then it resolves only from 2025 on (older filings use the old table)
        """
        recent = self.accounts.filtered(
            lambda a: a.date_start == fields.Date.to_date("2025-01-01")
        )[:1]
        self.assertTrue(recent)
        recent.account_ids = [(4, self.odoo_account.id)]
        self.assertFalse(self.plan.resolve(self.odoo_account, date="2024-12-31"))
        self.assertEqual(
            self.plan.resolve(self.odoo_account, date="2025-06-30"), recent
        )
        self.assertEqual(
            self.plan.sped_referential_line(self.odoo_account, date="2025-06-30"),
            {"COD_PLAN_REF": "1", "COD_CTA_REF": recent.code},
        )
        self.assertEqual(
            self.plan.sped_referential_line(self.odoo_account, date="2024-12-31"), {}
        )

    def test_plan_marks_mapped_count(self):
        """
        Given one Odoo account linked to the table
        When the plan counters are read
        Then mapped_count counts it
        """
        before = self.plan.mapped_count
        self._ref("1.01.01.01.01").account_ids = [(4, self.odoo_account.id)]
        self.assertEqual(self.plan.mapped_count, before + 1)
