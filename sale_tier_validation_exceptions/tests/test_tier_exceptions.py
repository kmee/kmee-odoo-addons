# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged

from .common import TierExceptionsMixin


@tagged("post_install", "-at_install")
class TestTierValidationExceptions(TierExceptionsMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_tier_exceptions()

    def _order_waiting_validation(self, price_unit=5000.0):
        order = self._order(price_unit)
        self.assertEqual(order.detect_exceptions(), [self.rule.id])
        order.request_validation()
        return order

    def test_tier_definition_is_shipped_for_orders_with_exceptions(self):
        """
        Given the data of the module
        When we read the tier definition it creates
        Then it applies to sale orders that have exceptions
        """
        self.assertEqual(self.tier.model, "sale.order")
        order = self._order(5000.0)
        self.assertFalse(order.evaluate_tier(self.tier))
        order.detect_exceptions()
        self.assertEqual(order.evaluate_tier(self.tier), order)

    def test_order_without_exception_needs_no_validation(self):
        """
        Given a small order that triggers no exception rule
        When exceptions are detected
        Then no exception is found and no tier validation is required
        """
        order = self._order(10.0)
        self.assertEqual(order.detect_exceptions(), [])
        self.assertFalse(order.need_validation)

    def test_order_with_exception_needs_validation(self):
        """
        Given a big order that triggers the exception rule
        When exceptions are detected
        Then the order needs tier validation
        """
        order = self._order(5000.0)
        order.detect_exceptions()
        self.assertEqual(order.exception_ids, self.rule)
        self.assertTrue(order.need_validation)

    def test_quotation_send_is_blocked_by_exceptions(self):
        """
        Given a quotation with a pending exception
        When the user tries to send it by e-mail
        Then the exceptions popup opens instead of the e-mail composer
        """
        order = self._order(5000.0)
        action = order.action_quotation_send()
        self.assertEqual(action["res_model"], "sale.exception.confirm")
        self.assertEqual(action["context"]["active_ids"], order.ids)

    def test_quotation_send_works_without_exceptions(self):
        """
        Given a quotation that has no exception
        When the user sends it by e-mail
        Then the standard e-mail composer is opened
        """
        order = self._order(10.0)
        action = order.action_quotation_send()
        self.assertEqual(action["res_model"], "mail.compose.message")

    def test_confirm_is_blocked_until_the_tier_is_validated(self):
        """
        Given an order with exceptions and a review pending for the approver
        When the order is confirmed before the approval
        Then the exceptions popup is shown and the order stays a quotation
        """
        order = self._order_waiting_validation()
        action = order.action_confirm()
        self.assertEqual(action["res_model"], "sale.exception.confirm")
        self.assertEqual(order.state, "draft")

    def test_approver_validation_ignores_exceptions_and_unblocks_confirm(self):
        """
        Given an order with exceptions waiting for the approver
        When the approver validates the tier
        Then the exceptions are ignored and the order can be confirmed
        """
        order = self._order_waiting_validation()
        self.assertEqual(order.validation_status, "pending")
        order.with_user(self.approver).validate_tier()
        self.assertEqual(order.validation_status, "validated")
        self.assertTrue(order.ignore_exception)
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_non_reviewer_cannot_ignore_exceptions_through_validate_tier(self):
        """
        Given an order with exceptions waiting for the approver
        When a salesman who is not a reviewer calls validate_tier
        Then nothing is validated and the exceptions are NOT ignored
        """
        order = self._order_waiting_validation()
        order.with_user(self.salesman).validate_tier()
        self.assertEqual(order.validation_status, "pending")
        self.assertFalse(order.ignore_exception)
        action = order.action_confirm()
        self.assertEqual(action["res_model"], "sale.exception.confirm")
        self.assertEqual(order.state, "draft")

    def test_blocking_exception_cannot_be_ignored_by_approval(self):
        """
        Given a blocking exception rule matching the order
        When the approver tries to validate the tier
        Then a UserError refuses to ignore the exception
        """
        self.rule.is_blocking = True
        order = self._order_waiting_validation()
        with self.assertRaises(UserError), self.env.cr.savepoint():
            order.with_user(self.approver).validate_tier()
        self.assertFalse(order.ignore_exception)

    def test_restart_validation_brings_exceptions_back(self):
        """
        Given an order whose exceptions were ignored after approval
        When the validation is restarted
        Then the reviews are removed and the exceptions are no longer ignored
        """
        order = self._order_waiting_validation()
        order.with_user(self.approver).validate_tier()
        self.assertTrue(order.ignore_exception)
        order.restart_validation()
        self.assertFalse(order.ignore_exception)
        self.assertFalse(order.review_ids)

    def test_ignore_exception_can_be_written_while_under_validation(self):
        """
        Given an order under validation (review pending)
        When the ignore flag is written, and then an ordinary field
        Then the flag is accepted but the ordinary field is blocked
        """
        order = self._order_waiting_validation()
        order.write({"ignore_exception": True})
        self.assertTrue(order.ignore_exception)
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            order.write({"client_order_ref": "REF"})

    def test_validation_exceptions_include_exception_fields(self):
        """
        Given the list of fields allowed to change under validation
        When asked to the sale order
        Then exception_ids and ignore_exception are part of it
        """
        fields_ok = self.env["sale.order"]._get_validation_exceptions()
        self.assertIn("ignore_exception", fields_ok)
        self.assertIn("exception_ids", fields_ok)

    def test_views_hide_manual_ignore_controls(self):
        """
        Given the sale order form, the exception rule form and the confirm wizard
        When the combined views are read
        Then the ignore button, the blocking flag and the ignore checkbox are
        hidden, while the views they come from show them
        """
        cases = (
            (
                "sale.view_order_form",
                "sale_exception.view_order_form",
                "//button[@name='action_ignore_exceptions']",
            ),
            (
                "base_exception.view_exception_rule_form",
                None,
                "//field[@name='is_blocking']",
            ),
            (
                "sale_exception.view_sale_exception_confirm",
                None,
                "//field[@name='ignore']",
            ),
        )
        for root_xmlid, original_xmlid, xpath in cases:
            combined = etree.fromstring(self.env.ref(root_xmlid).get_combined_arch())
            nodes = combined.xpath(xpath)
            self.assertEqual(len(nodes), 1, xpath)
            self.assertEqual(nodes[0].get("invisible"), "True", xpath)
            # control: the original definition does not hide the control
            original = etree.fromstring(
                self.env.ref(original_xmlid or root_xmlid).arch_db
            ).xpath(xpath)
            self.assertNotEqual(original[0].get("invisible"), "True", xpath)
