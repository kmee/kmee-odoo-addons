# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBantScores(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.lead = cls.env["crm.lead"].create({"name": "BANT lead"})

    def test_empty_lead_is_unqualified(self):
        self.assertEqual(self.lead.bant_total_score, 0)
        self.assertEqual(self.lead.bant_qualification_status, "unqualified")
        self.assertEqual(self.lead.bant_progress, 0)

    def test_partially_qualified(self):
        self.lead.write(
            {"bant_budget_status": "budget_defined", "bant_need_status": "important"}
        )
        self.assertEqual(self.lead.bant_total_score, 4)
        self.assertEqual(self.lead.bant_qualification_status, "partially_qualified")

    def test_fully_qualified(self):
        self.lead.write(
            {
                "bant_budget_status": "budget_approved",
                "bant_authority_status": "decision_maker",
                "bant_need_status": "critical",
                "bant_timeline_status": "immediate",
            }
        )
        self.assertEqual(self.lead.bant_total_score, 12)
        self.assertEqual(self.lead.bant_qualification_status, "fully_qualified")
        self.assertEqual(self.lead.bant_progress, 100)

    def test_high_score_without_all_dimensions_is_only_qualified(self):
        self.lead.write(
            {
                "bant_budget_status": "budget_approved",
                "bant_authority_status": "decision_maker",
                "bant_need_status": "critical",
            }
        )
        self.assertEqual(self.lead.bant_total_score, 9)
        self.assertEqual(self.lead.bant_qualification_status, "qualified")
