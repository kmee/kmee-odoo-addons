# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleCrmAutoWon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, no_reset_password=True)
        )
        cls.partner = cls.env["res.partner"].create({"name": "Auto Won Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "Auto Won Service", "type": "service", "list_price": 50.0}
        )
        cls.won_stage = cls.env["crm.stage"].search([("is_won", "=", True)], limit=1)

    def _lead(self, name="Opportunity"):
        return self.env["crm.lead"].create(
            {
                "name": name,
                "type": "opportunity",
                "partner_id": self.partner.id,
                "expected_revenue": 50.0,
            }
        )

    def _order(self, lead=None):
        vals = {
            "partner_id": self.partner.id,
            "order_line": [
                (0, 0, {"product_id": self.product.id, "product_uom_qty": 1})
            ],
        }
        if lead:
            vals["opportunity_id"] = lead.id
        return self.env["sale.order"].create(vals)

    def test_confirm_marks_opportunity_won(self):
        """
        Given a quotation linked to an open opportunity
        When the quotation is confirmed
        Then the opportunity is moved to the won stage with 100% probability
        """
        lead = self._lead()
        self.assertFalse(lead.stage_id.is_won)
        order = self._order(lead)
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertTrue(lead.stage_id.is_won)
        self.assertEqual(lead.stage_id, self.won_stage)
        self.assertEqual(lead.probability, 100.0)

    def test_draft_quotation_keeps_opportunity_open(self):
        """
        Given a quotation linked to an opportunity that is not confirmed
        When the quotation is only created
        Then the opportunity is not won
        """
        lead = self._lead()
        self._order(lead)
        self.assertFalse(lead.stage_id.is_won)
        self.assertLess(lead.probability, 100.0)

    def test_confirm_without_opportunity_works(self):
        """
        Given a quotation without opportunity
        When it is confirmed
        Then it is confirmed normally and no lead is touched
        """
        other_lead = self._lead("Unrelated")
        order = self._order()
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertFalse(other_lead.stage_id.is_won)

    def test_confirm_many_orders_marks_only_linked_opportunities(self):
        """
        Given two quotations, one linked to an opportunity and one not
        When both are confirmed together
        Then only the linked opportunity is won
        """
        lead = self._lead()
        untouched = self._lead("Untouched")
        orders = self._order(lead) | self._order()
        orders.action_confirm()
        self.assertEqual(orders.mapped("state"), ["sale", "sale"])
        self.assertTrue(lead.stage_id.is_won)
        self.assertFalse(untouched.stage_id.is_won)

    def test_already_won_opportunity_stays_won(self):
        """
        Given an opportunity already won
        When a linked quotation is confirmed
        Then the opportunity remains won and the order is confirmed
        """
        lead = self._lead()
        lead.action_set_won()
        order = self._order(lead)
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertTrue(lead.stage_id.is_won)
