# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.purchase_rfq_round.tests.common import RfqRoundCommon


@tagged("post_install", "-at_install")
class TestPurchaseRfqComparison(RfqRoundCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.term_now = cls.env.ref("account.account_payment_term_immediate")
        cls.term_30 = cls.env.ref("account.account_payment_term_30days")
        cls.product_a.seller_ids.filtered(
            lambda s: s.partner_id == cls.vendor_1
        ).rfq_approved = True

    def setUp(self):
        super().setUp()
        self.rfq_round = self._make_round(self.vendor_1 | self.vendor_2)
        self.rfq_round.action_create_rfqs()
        self.quote_1 = self._quote(self.rfq_round, self.vendor_1, self.product_a)
        self.quote_2 = self._quote(self.rfq_round, self.vendor_2, self.product_a)
        self.line_a = self.rfq_round.line_ids.filtered(
            lambda r: r.product_id == self.product_a
        )
        date_order = self.quote_1.order_id.date_order
        self.quote_1.write(
            {
                "price_unit": 9.0,
                "rfq_payment_term_id": self.term_now.id,
                "date_planned": date_order + timedelta(days=10),
            }
        )
        self.quote_2.write(
            {
                "price_unit": 9.05,
                "rfq_payment_term_id": self.term_30.id,
                "date_planned": date_order + timedelta(days=10),
            }
        )

    def test_01_approved_vendor_flag(self):
        self.assertTrue(self.quote_1.rfq_vendor_approved)
        self.assertTrue(self.quote_1.rfq_spec_approved)
        self.assertFalse(self.quote_2.rfq_vendor_approved)

    def test_02_present_value(self):
        self.assertEqual(self.quote_1.rfq_payment_days, 0.0)
        self.assertEqual(self.quote_2.rfq_payment_days, 30.0)
        self.assertAlmostEqual(
            self.quote_1.rfq_present_value, self.quote_1.price_total, places=2
        )
        self.assertAlmostEqual(
            self.quote_2.rfq_present_value, self.quote_2.price_total / 1.01, places=2
        )

    def test_03_score_present_value_favours_longer_terms(self):
        self.rfq_round.price_basis = "present_value"
        self.rfq_round.action_award_best_score()
        self.assertEqual(self.line_a.awarded_partner_id, self.vendor_2)
        self.assertAlmostEqual(self.quote_2.rfq_score, 100.0, places=1)
        self.assertLess(self.quote_1.rfq_score, 100.0)

    def test_04_score_subtotal(self):
        self.rfq_round.price_basis = "subtotal"
        self.rfq_round.action_award_best_score()
        self.assertEqual(self.line_a.awarded_partner_id, self.vendor_1)

    def test_05_lead_time_weight(self):
        self.rfq_round.write(
            {"price_basis": "subtotal", "weight_price": 10.0, "weight_delay": 90.0}
        )
        self.quote_1.date_planned = self.quote_1.order_id.date_order + timedelta(
            days=40
        )
        self.rfq_round.action_award_best_score()
        self.assertEqual(self.line_a.awarded_partner_id, self.vendor_2)

    def test_06_require_approved(self):
        self.rfq_round.write({"price_basis": "present_value", "require_approved": True})
        self.rfq_round.action_award_best_score()
        self.assertEqual(self.line_a.awarded_partner_id, self.vendor_1)
        self.assertFalse(self.quote_2.rfq_eligible)
        self.assertEqual(self.quote_2.rfq_score, 0.0)

    def test_07_expired_quote_not_eligible(self):
        self.quote_2.rfq_validity_date = fields.Date.today() - timedelta(days=1)
        self.rfq_round.action_award_best_score()
        self.assertEqual(self.line_a.awarded_partner_id, self.vendor_1)

    def test_08_award_wizard_default_score(self):
        self.rfq_round.price_basis = "present_value"
        action = self.rfq_round.action_open_award()
        wizard = (
            self.env[action["res_model"]].with_context(**action["context"]).create({})
        )
        self.assertEqual(wizard.criterion, "score")
        wizard.action_apply()
        self.assertEqual(self.line_a.awarded_partner_id, self.vendor_2)
