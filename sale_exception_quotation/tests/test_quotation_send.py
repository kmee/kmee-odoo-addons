# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleExceptionQuotation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, no_reset_password=True)
        )
        cls.rule = cls.env.ref("sale_exception.excep_no_zip").sudo()
        cls.rule.active = True
        cls.partner = cls.env["res.partner"].create(
            {"name": "Zip Customer", "email": "zip@example.com"}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Exception Service", "type": "service", "list_price": 10.0}
        )

    def _order(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 1})
                ],
            }
        )

    def test_send_blocked_when_exception_detected(self):
        """
        Given a quotation whose customer has no zip code (active exception rule)
        When the user clicks to send the quotation by e-mail
        Then the exception popup is returned instead of the mail composer
        and the exception is recorded on the order
        """
        self.partner.zip = False
        order = self._order()
        action = order.action_quotation_send()
        self.assertEqual(action["res_model"], "sale.exception.confirm")
        self.assertIn(self.rule, order.exception_ids)
        self.assertEqual(action["context"]["active_ids"], order.ids)

    def test_send_allowed_without_exception(self):
        """
        Given a quotation whose customer has a zip code
        When the user clicks to send the quotation by e-mail
        Then the standard mail composer action is returned
        """
        self.partner.zip = "12345"
        order = self._order()
        action = order.action_quotation_send()
        self.assertEqual(action["res_model"], "mail.compose.message")
        self.assertFalse(order.exception_ids)

    def test_send_allowed_when_rule_is_inactive(self):
        """
        Given a customer without zip but the exception rule disabled
        When the user clicks to send the quotation
        Then the mail composer is returned (no exception is detected)
        """
        self.partner.zip = False
        self.rule.active = False
        order = self._order()
        action = order.action_quotation_send()
        self.assertEqual(action["res_model"], "mail.compose.message")

    def test_send_allowed_after_ignoring_exception(self):
        """
        Given a quotation with a detected exception that was ignored
        When the user clicks to send the quotation
        Then the mail composer is returned
        """
        self.partner.zip = False
        order = self._order()
        order.ignore_exception = True
        action = order.action_quotation_send()
        self.assertEqual(action["res_model"], "mail.compose.message")

    def test_exception_does_not_change_quotation_state(self):
        """
        Given a quotation with a detected exception
        When sending is blocked
        Then the quotation stays in draft (not marked as sent)
        """
        self.partner.zip = False
        order = self._order()
        order.action_quotation_send()
        self.assertEqual(order.state, "draft")
