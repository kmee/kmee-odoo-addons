# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDemo(TransactionCase):
    """The demo boletos cover the matching cases (checked by number)."""

    def setUp(self):
        super().setUp()
        sources = self.env["l10n_br_dda.debit.source"].search(
            [("source_key", "=", "demo")]
        )
        if not sources:
            self.skipTest("Demo data not loaded (or the company had no chart).")
        self.debits = sources.debit_id
        self.by_ext = {s.external_id: s.debit_id for s in sources}

    def test_demo_cases(self):
        self.assertEqual(len(self.debits), 12)
        cases = self.by_ext
        self.assertEqual(cases["demo-1"].state, "suggested")
        self.assertEqual(cases["demo-1"].recommended_action, "link")
        self.assertEqual(cases["demo-2"].recommended_action, "review")
        self.assertEqual(cases["demo-2"].divergence_amount, 87.5)
        self.assertEqual(cases["demo-3"].recommended_action, "review")
        self.assertEqual(len(cases["demo-4"].match_ids), 2)
        self.assertEqual(cases["demo-4"].recommended_action, "review")
        self.assertEqual(cases["demo-5"].recommended_action, "review")
        self.assertEqual(cases["demo-6"].match_ids.identity_kind, "assignment")
        self.assertEqual(cases["demo-6"].recommended_action, "review")
        self.assertEqual(cases["demo-7"].state, "suspect")
        self.assertEqual(cases["demo-8"].recommended_action, "link_many")
        self.assertEqual(cases["demo-9"].recommended_action, "create_bill")
        self.assertEqual(cases["demo-10"].recommended_action, "link")
        self.assertIn("possible_duplicate", cases["demo-11"].alert_codes)
        self.assertIn("possible_duplicate", cases["demo-12"].alert_codes)
