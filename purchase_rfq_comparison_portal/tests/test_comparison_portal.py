# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.purchase_rfq_round_portal.tests.test_portal import RfqRoundPortalCommon


@tagged("post_install", "-at_install")
class TestComparisonPortal(RfqRoundPortalCommon):
    def test_10_answer_with_criteria(self):
        term_30 = self.env.ref("account.account_payment_term_30days")
        validity = fields.Date.today() + timedelta(days=15)
        page = self.url_open(self._url())
        self.assertIn(f"payment_term_{self.line_a.id}", page.text)
        self._post(
            {
                f"price_unit_{self.line_a.id}": "11",
                f"payment_term_{self.line_a.id}": str(term_30.id),
                f"validity_{self.line_a.id}": str(validity),
                f"min_qty_{self.line_a.id}": "50",
                f"spec_{self.line_a.id}": "1",
                # Item B sem preço: a caixa desmarcada não vira resposta.
                f"price_unit_{self.line_b.id}": "",
            }
        )
        self.assertEqual(self.line_a.rfq_payment_term_id, term_30)
        self.assertEqual(self.line_a.rfq_validity_date, validity)
        self.assertEqual(self.line_a.rfq_min_qty, 50.0)
        self.assertTrue(self.line_a.rfq_spec_approved)
        self.assertGreater(self.line_a.rfq_score, 0.0)
        self.assertEqual(len(self.rfq_round.response_ids), 1)

    def test_11_validity_in_the_past(self):
        response = self._post(
            {
                f"price_unit_{self.line_a.id}": "11",
                f"validity_{self.line_a.id}": str(
                    fields.Date.today() - timedelta(days=1)
                ),
            }
        )
        self.assertIn("cannot be in the past", response.text)
        self.assertEqual(self.line_a.price_unit, 0.0)
