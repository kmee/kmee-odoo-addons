# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestContractJournal(TransactionCase):
    def test_contract_default_journal_is_fopag(self):
        fopag = self.env.ref("l10n_br_hr_payroll_account.journal_folha_pagamento")
        default = self.env["hr.contract"].default_get(["journal_id"])
        self.assertEqual(default.get("journal_id"), fopag.id)

    def test_payroll_journal_helper(self):
        journal = self.env["account.journal"]._l10n_br_payroll_journal()
        self.assertTrue(journal)
