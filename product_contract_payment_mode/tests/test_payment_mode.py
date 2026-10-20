# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductContractPaymentMode(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                tracking_disable=True,
                test_queue_job_no_delay=True,
                no_reset_password=True,
            )
        )
        method = cls.env.ref("account.account_payment_method_manual_in")
        PaymentMode = cls.env["account.payment.mode"]
        cls.mode_a = PaymentMode.create(
            {
                "name": "Mode A",
                "bank_account_link": "variable",
                "payment_method_id": method.id,
            }
        )
        cls.mode_b = PaymentMode.create(
            {
                "name": "Mode B",
                "bank_account_link": "variable",
                "payment_method_id": method.id,
            }
        )
        cls.template = cls.env["contract.template"].create({"name": "Template"})
        cls.service = cls.env["product.product"].create(
            {
                "name": "Recurring service",
                "type": "service",
                "is_contract": True,
                "list_price": 100.0,
                "property_contract_template_id": cls.template.id,
            }
        )
        cls.plain_service = cls.env["product.product"].create(
            {"name": "Plain service", "type": "service", "list_price": 10.0}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})

    def _order(self, payment_mode, product=None):
        vals = {
            "partner_id": self.partner.id,
            "payment_mode_id": payment_mode.id,
            "order_line": [
                (
                    0,
                    0,
                    {
                        "product_id": (product or self.service).id,
                        "product_uom_qty": 1.0,
                        "price_unit": 100.0,
                    },
                )
            ],
        }
        if "fiscal_operation_id" in self.env["sale.order"]._fields:
            vals["fiscal_operation_id"] = False
        return self.env["sale.order"].create(vals)

    def test_contract_created_from_order_inherits_payment_mode(self):
        """Given an order with payment mode A and a contract product,
        When the contract is generated from the order,
        Then the contract has payment mode A."""
        order = self._order(self.mode_a)
        contract = order.action_create_contract()
        self.assertEqual(len(contract), 1)
        self.assertEqual(contract.payment_mode_id, self.mode_a)
        self.assertEqual(order.order_line.contract_id, contract)

    def test_prepare_contract_value_without_payment_mode(self):
        """Given an order with no payment mode,
        When the contract values are prepared,
        Then payment_mode_id is falsy (no stale value leaks in)."""
        order = self._order(self.env["account.payment.mode"])
        values = order._prepare_contract_value(self.template)
        self.assertFalse(values["payment_mode_id"])
        contract = order.action_create_contract()
        self.assertFalse(contract.payment_mode_id)

    def test_prepare_contract_value_carries_payment_mode(self):
        """Given an order with payment mode B,
        When values are prepared for a template,
        Then payment_mode_id is mode B and the base values are kept."""
        order = self._order(self.mode_b)
        values = order._prepare_contract_value(self.template)
        self.assertEqual(values["payment_mode_id"], self.mode_b.id)
        self.assertEqual(values["partner_id"], self.partner.id)
        self.assertEqual(values["contract_template_id"], self.template.id)

    def test_change_order_payment_mode_updates_contract(self):
        """Given a contract generated with mode A,
        When the order payment mode changes to B (onchange),
        Then the contract payment mode becomes B."""
        order = self._order(self.mode_a)
        contract = order.action_create_contract()
        self.assertEqual(contract.payment_mode_id, self.mode_a)
        order.payment_mode_id = self.mode_b
        order._onchange_payment_mode_id()
        self.assertEqual(contract.payment_mode_id, self.mode_b)

    def test_clear_order_payment_mode_clears_contract(self):
        """Given a contract with mode A,
        When the order payment mode is cleared,
        Then the contract payment mode is cleared too."""
        order = self._order(self.mode_a)
        contract = order.action_create_contract()
        order.payment_mode_id = False
        order._onchange_payment_mode_id()
        self.assertFalse(contract.payment_mode_id)

    def test_onchange_without_contract_is_noop(self):
        """Given an order whose lines are not contract products,
        When the payment mode changes,
        Then nothing breaks and no contract exists."""
        order = self._order(self.mode_a, product=self.plain_service)
        self.assertFalse(order.is_contract)
        order.payment_mode_id = self.mode_b
        order._onchange_payment_mode_id()
        self.assertFalse(order.order_line.contract_id)

    def test_onchange_does_not_touch_other_orders_contract(self):
        """Given two orders each with their own contract,
        When one order changes payment mode,
        Then only its own contract changes."""
        order1 = self._order(self.mode_a)
        order2 = self._order(self.mode_a)
        contract1 = order1.action_create_contract()
        contract2 = order2.action_create_contract()
        order1.payment_mode_id = self.mode_b
        order1._onchange_payment_mode_id()
        self.assertEqual(contract1.payment_mode_id, self.mode_b)
        self.assertEqual(contract2.payment_mode_id, self.mode_a)

    def test_invoice_from_contract_carries_payment_mode(self):
        """Given a contract created from an order with mode A,
        When the contract invoice values are prepared,
        Then the invoice carries mode A."""
        order = self._order(self.mode_a)
        contract = order.action_create_contract()
        vals = contract._prepare_invoice(contract.recurring_next_date)
        self.assertEqual(vals["payment_mode_id"], self.mode_a.id)
