# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCrmPredictRevenue(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lead = cls.env["crm.lead"].create(
            {"name": "Lead", "type": "opportunity", "expected_revenue": 1000.0}
        )

    def test_weighted_revenue(self):
        self.lead.probability = 50
        self.assertAlmostEqual(self.lead.weighted_revenue, 500.0)
        self.lead.probability = 0
        self.assertEqual(self.lead.weighted_revenue, 0)

    def test_outreach_count(self):
        self.assertEqual(self.lead.outreach_count, 0)
        self.lead.activity_schedule(
            "mail.mail_activity_data_todo", summary="Call", user_id=self.env.uid
        )
        self.lead.invalidate_recordset()
        self.assertEqual(self.lead.outreach_count, 1)
        self.assertTrue(self.lead.last_activity_date)

    def test_sales_cycle_won(self):
        self.lead.action_set_won()
        self.assertTrue(self.lead.date_closed)
        self.assertEqual(self.lead.lost_sales_cycle_days, 0)
        self.assertLessEqual(abs(self.lead.won_sales_cycle_days), 1)

    def test_days_in_current_stage(self):
        self.lead.date_last_stage_update = fields.Datetime.now()
        self.assertEqual(self.lead.days_in_current_stage, 0)
