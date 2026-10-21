# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests.common import TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install")
class TestSalePartialLock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.to_invoice = cls.env["product.product"].create(
            {"name": "Ordered quantities", "type": "service", "invoice_policy": "order"}
        )
        cls.not_invoiceable = cls.env["product.product"].create(
            {
                "name": "Delivered quantities",
                "type": "service",
                "invoice_policy": "delivery",
            }
        )
        root = etree.fromstring(
            cls.env["sale.order"].get_view(
                cls.env.ref("sale.view_order_form").id, "form"
            )["arch"]
        )
        cls.cancel_button = root.xpath(
            "//header/button[@name='action_draft']/following-sibling::button[1]"
        )[0]
        cls.invoice_button = root.xpath(
            "//header/button[@name='payment_action_void']/following-sibling::button[1]"
        )[0]
        cls.core_cancel_buttons = etree.fromstring(
            cls.env.ref("sale.view_order_form").arch_db
        ).xpath("//header/button[@name='action_cancel']")

    def _order(self, product, locked=False, confirmed=True):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 2.0})
                ],
            }
        )
        if confirmed:
            # write the state: other sale modules (e.g. isolated quotation) may
            # turn action_confirm into a wizard when installed in the same database
            order.state = "sale"
        if locked:
            order.action_lock()
        return order

    def _is_visible(self, node, order):
        """Evaluate the invisible expression of a button against one order."""
        invisible = node.get("invisible")
        if not invisible:
            return True
        values = {
            name: order[name] for name in ("id", "state", "locked", "invoice_status")
        }
        return not safe_eval(invisible, values)

    def test_cancel_button_is_only_visible_on_locked_orders(self):
        """
        Given the extra Cancel button added by the module
        When it is evaluated against orders in each state
        Then it is visible only for locked orders
        """
        draft = self._order(self.to_invoice, confirmed=False)
        sale = self._order(self.to_invoice)
        locked = self._order(self.to_invoice, locked=True)
        self.assertEqual(self.cancel_button.get("name"), "action_cancel")
        self.assertFalse(self._is_visible(self.cancel_button, draft))
        self.assertFalse(self._is_visible(self.cancel_button, sale))
        self.assertTrue(self._is_visible(self.cancel_button, locked))

    def test_core_cancel_buttons_do_not_cover_locked_orders(self):
        """
        Given the core Cancel buttons of the form
        When we read the states they are shown for
        Then all of them are hidden on locked orders, which is why the module
        adds one
        """
        self.assertTrue(self.core_cancel_buttons)
        for button in self.core_cancel_buttons:
            self.assertIn("locked", button.get("invisible") or "")

    def test_invoice_button_visible_on_locked_order_with_nothing_to_invoice(self):
        """
        Given a locked order whose invoice status is not 'to invoice'
        When the extra Create Invoice button is evaluated
        Then it is visible, while for an unlocked order in the same status it is not
        """
        locked = self._order(self.not_invoiceable, locked=True)
        unlocked = self._order(self.not_invoiceable)
        self.assertEqual(locked.invoice_status, "no")
        self.assertEqual(unlocked.invoice_status, "no")
        self.assertTrue(self._is_visible(self.invoice_button, locked))
        self.assertFalse(self._is_visible(self.invoice_button, unlocked))

    def test_invoice_button_visible_when_there_is_something_to_invoice(self):
        """
        Given orders with something to invoice, locked or not
        When the extra Create Invoice button is evaluated
        Then it is visible in both cases
        """
        unlocked = self._order(self.to_invoice)
        locked = self._order(self.to_invoice, locked=True)
        self.assertEqual(unlocked.invoice_status, "to invoice")
        self.assertEqual(locked.invoice_status, "to invoice")
        self.assertTrue(self._is_visible(self.invoice_button, unlocked))
        self.assertTrue(self._is_visible(self.invoice_button, locked))

    def test_invoice_button_opens_the_advance_payment_wizard(self):
        """
        Given the extra Create Invoice button
        When we resolve its action
        Then it opens the sale.advance.payment.inv wizard
        """
        action = self.env["ir.actions.actions"].browse(
            int(self.invoice_button.get("name"))
        )
        action = self.env[action.type].browse(action.id)
        self.assertEqual(action.res_model, "sale.advance.payment.inv")
        self.assertEqual(self.invoice_button.get("type"), "action")

    def test_locked_order_can_be_cancelled(self):
        """
        Given a locked order
        When the Cancel button method runs (without the confirmation wizard)
        Then the order is cancelled; with the wizard it asks for confirmation first
        """
        locked = self._order(self.to_invoice, locked=True)
        action = locked.action_cancel()
        self.assertEqual(action["res_model"], "sale.order.cancel")
        self.assertEqual(locked.state, "sale")
        self.assertTrue(locked.locked)
        locked.with_context(disable_cancel_warning=True).action_cancel()
        self.assertEqual(locked.state, "cancel")

    def test_locked_order_can_still_be_invoiced_through_the_wizard(self):
        """
        Given a locked order with quantities to invoice
        When the advance payment wizard is opened and validated for it
        Then it targets the order and accepts the delivered/ordered method
        """
        locked = self._order(self.to_invoice, locked=True)
        wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_model="sale.order", active_ids=locked.ids)
            .create({"advance_payment_method": "delivered"})
        )
        self.assertEqual(wizard.count, 1)
        self.assertEqual(wizard.advance_payment_method, "delivered")
        self.assertTrue(locked.locked)
