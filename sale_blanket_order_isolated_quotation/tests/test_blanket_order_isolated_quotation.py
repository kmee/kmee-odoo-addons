# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBlanketOrderIsolatedQuotation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, no_reset_password=True)
        )
        # the model compares the validity date with fields.Date.today() (UTC)
        cls.today = fields.Date.today()
        cls.partner = cls.env["res.partner"].create({"name": "BO Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "BO Service", "type": "service", "list_price": 100.0}
        )
        cls.product_2 = cls.env["product.product"].create(
            {"name": "BO Service 2", "type": "service", "list_price": 50.0}
        )
        cls.pricelist = cls.env["product.pricelist"].create(
            {"name": "BO Pricelist", "currency_id": cls.env.company.currency_id.id}
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _bo_line_vals(self, product, qty, price):
        return (
            0,
            0,
            {
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "price_unit": price,
                "original_uom_qty": qty,
            },
        )

    def _blanket_order(self, confirm=True, qty=10.0):
        blanket = self.env["sale.blanket.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist.id,
                "validity_date": self.today + timedelta(days=30),
                "line_ids": [self._bo_line_vals(self.product, qty, 100.0)],
            }
        )
        if confirm:
            blanket.action_confirm()
        return blanket

    def _quotation(self, qty=4.0, price=100.0):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist.id,
                "validity_date": self.today + timedelta(days=30),
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                            "price_unit": price,
                        },
                    )
                ],
            }
        )

    def _wizard(self, quotation):
        return self.env["sale.order.confirm"].create({"sale_id": quotation.id})

    def _reference_quotation(self, blanket):
        action = blanket.action_create_reference_quotation()
        return self.env["sale.order"].browse(action["res_id"])

    def _increment_quotation(self, blanket):
        action = blanket.action_create_increment_quotation()
        return self.env["sale.order"].browse(action["res_id"])

    # ------------------------------------------------------------------
    # Quotation confirmation: choice wizard
    # ------------------------------------------------------------------
    def test_quotation_confirm_opens_choice_wizard(self):
        """
        Given a normal quotation (not yet an order)
        When the user confirms it
        Then the choice wizard is returned and the quotation stays in draft
        """
        quotation = self._quotation()
        action = quotation.action_confirm()
        self.assertEqual(action["res_model"], "sale.order.confirm")
        self.assertEqual(action["context"]["default_sale_id"], quotation.id)
        self.assertEqual(quotation.state, "draft")

    def test_order_sequence_confirm_is_standard(self):
        """
        Given a quotation already converted into a numbered sale order
        When it is confirmed
        Then the standard confirmation happens without the choice wizard
        """
        order = self._quotation()
        order.order_sequence = True
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_batch_confirm_of_numbered_orders(self):
        """
        Given two quotations already converted into numbered sale orders
        When they are confirmed together (list action, server action, other module)
        Then both go through the standard confirmation
        """
        orders = self._quotation() | self._quotation(qty=2.0)
        orders.write({"order_sequence": True})
        orders.action_confirm()
        self.assertEqual(orders.mapped("state"), ["sale", "sale"])

    def test_batch_confirm_of_reference_quotations(self):
        """
        Given two reference quotations of 3 and 2 units of a 10 unit blanket order
        When they are confirmed together
        Then each one generates its confirmed sale order and the balance drops to 5
        """
        blanket = self._blanket_order()
        first = self._reference_quotation(blanket)
        first.order_line.product_uom_qty = 3.0
        second = self._reference_quotation(blanket)
        second.order_line.product_uom_qty = 2.0
        (first | second).action_confirm()
        orders = self.env["sale.order"].search(
            [("quote_id", "in", (first | second).ids)]
        )
        self.assertEqual(orders.mapped("state"), ["sale", "sale"])
        self.assertEqual(blanket.line_ids.ordered_uom_qty, 5.0)
        self.assertEqual(blanket.line_ids.remaining_uom_qty, 5.0)

    def test_batch_confirm_with_plain_quotation_is_refused(self):
        """
        Given a plain quotation (it needs the choice wizard) and a numbered order
        When they are confirmed together
        Then a user error asks to confirm the quotation alone and nothing changes
        """
        quotation = self._quotation()
        order = self._quotation(qty=2.0)
        order.order_sequence = True
        with self.assertRaises(UserError):
            (quotation | order).action_confirm()
        self.assertEqual(order.state, "draft")
        self.assertEqual(quotation.state, "draft")

    def test_wizard_create_normal_order(self):
        """
        Given a quotation and the choice wizard
        When the user picks "Create Sale Order"
        Then a numbered sale order is created from the quotation, linked to it,
        and the quotation is closed
        """
        quotation = self._quotation()
        action = self._wizard(quotation).create_normal_order()
        order = quotation.order_id
        self.assertTrue(order)
        self.assertTrue(order.order_sequence)
        self.assertEqual(order.quote_id, quotation)
        self.assertEqual(order.order_line.product_uom_qty, 4.0)
        self.assertEqual(quotation.state, "done")
        self.assertEqual(action["res_id"], order.id)

    def test_wizard_create_blanket_order(self):
        """
        Given a quotation of 4 units at 100 and the choice wizard
        When the user picks "Create Blanket Order"
        Then a confirmed blanket order is created with the same partner,
        lines and the quotation data, the quotation is closed and linked
        """
        quotation = self._quotation()
        action = self._wizard(quotation).create_blanket_order()
        blanket = self.env["sale.blanket.order"].browse(action["res_id"])
        self.assertEqual(blanket.partner_id, self.partner)
        self.assertEqual(blanket.isolated_quotation_id, quotation)
        self.assertEqual(quotation.blanket_order_id, blanket)
        self.assertEqual(quotation.state, "done")
        self.assertEqual(blanket.state, "open")
        self.assertNotEqual(blanket.name, "Draft")
        self.assertEqual(len(blanket.line_ids), 1)
        line = blanket.line_ids
        self.assertEqual(line.product_id, self.product)
        self.assertEqual(line.original_uom_qty, 4.0)
        self.assertEqual(line.price_unit, 100.0)
        self.assertTrue(blanket.quotation_data_json)

    # ------------------------------------------------------------------
    # Blanket order helpers
    # ------------------------------------------------------------------
    def test_blanket_state_open_when_validity_in_future(self):
        """
        Given a blanket order valid until a future date
        When its state is computed
        Then it is open
        """
        blanket = self._blanket_order(confirm=False)
        self.assertEqual(blanket.state, "open")

    def test_blanket_state_expired_when_validity_passed(self):
        """
        Given a blanket order whose validity date is today or in the past
        When its state is computed
        Then it is expired
        """
        blanket = self._blanket_order(confirm=False)
        blanket.validity_date = self.today
        blanket._compute_state()
        self.assertEqual(blanket.state, "expired")

    def test_blanket_line_discount_reduces_subtotal(self):
        """
        Given a blanket line of 2 units at 100 with 10% discount
        When the amounts are computed
        Then the subtotal is 180
        """
        blanket = self._blanket_order(confirm=False, qty=2.0)
        line = blanket.line_ids
        self.assertEqual(line.price_subtotal, 200.0)
        line.discount = 10.0
        self.assertAlmostEqual(line.price_subtotal, 180.0)
        self.assertAlmostEqual(line.price_total, 180.0)

    def test_blanket_line_discount_with_taxes(self):
        """
        Given a blanket line with a 10% tax and a 50% discount
        When the amounts are computed
        Then tax and total follow the discounted price
        """
        tax = self.env["account.tax"].create(
            {
                "name": "BO Tax 10",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )
        blanket = self._blanket_order(confirm=False, qty=2.0)
        line = blanket.line_ids
        line.write({"taxes_id": [(6, 0, tax.ids)], "discount": 50.0})
        self.assertAlmostEqual(line.price_subtotal, 100.0)
        self.assertAlmostEqual(line.price_tax, 10.0)
        self.assertAlmostEqual(line.price_total, 110.0)

    # ------------------------------------------------------------------
    # Reference quotation (consume balance)
    # ------------------------------------------------------------------
    def test_reference_quotation_copies_blanket_lines_with_zero_qty(self):
        """
        Given an open blanket order of 10 units
        When the user creates a reference quotation
        Then a quotation of type reference is created with one line per
        blanket line at zero quantity, showing original and available balance
        """
        blanket = self._blanket_order()
        quotation = self._reference_quotation(blanket)
        self.assertEqual(quotation.blanket_order_type, "reference")
        self.assertEqual(quotation.partner_id, self.partner)
        line = quotation.order_line
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_uom_qty, 0.0)
        self.assertEqual(line.original_bo_qty, 10.0)
        self.assertEqual(line.available_bo_qty, 10.0)
        self.assertEqual(line.blanket_order_line_id, blanket.line_ids)

    def test_confirm_reference_quotation_consumes_balance(self):
        """
        Given a reference quotation requesting 3 of 10 units
        When it is confirmed
        Then a confirmed sale order of 3 units is created and the blanket
        balance drops to 7
        """
        blanket = self._blanket_order()
        quotation = self._reference_quotation(blanket)
        quotation.order_line.product_uom_qty = 3.0
        action = quotation.action_confirm()
        order = self.env["sale.order"].browse(action["res_id"])
        self.assertEqual(order.state, "sale")
        self.assertEqual(order.quote_id, quotation)
        self.assertEqual(order.order_line.product_uom_qty, 3.0)
        self.assertEqual(blanket.line_ids.ordered_uom_qty, 3.0)
        self.assertEqual(blanket.line_ids.remaining_uom_qty, 7.0)
        self.assertEqual(order.order_line.blanket_order_line, blanket.line_ids)

    def test_confirm_reference_quotation_keeps_discount(self):
        """
        Given a reference quotation line with a discount
        When it is confirmed
        Then the generated sale order line carries the same discount
        """
        blanket = self._blanket_order()
        quotation = self._reference_quotation(blanket)
        quotation.order_line.write({"product_uom_qty": 2.0, "discount": 15.0})
        action = quotation.action_confirm()
        order = self.env["sale.order"].browse(action["res_id"])
        self.assertEqual(order.order_line.discount, 15.0)

    def test_confirm_reference_above_balance_is_blocked(self):
        """
        Given a reference quotation requesting 11 of 10 available units
        When it is confirmed
        Then a validation error is raised and no balance is consumed
        """
        blanket = self._blanket_order()
        quotation = self._reference_quotation(blanket)
        quotation.order_line.product_uom_qty = 11.0
        with self.assertRaises(ValidationError):
            quotation.action_confirm()
        self.assertEqual(blanket.line_ids.remaining_uom_qty, 10.0)

    def test_reference_line_warns_when_qty_exceeds_balance(self):
        """
        Given a reference quotation line requesting more than the balance
        When the quantity onchange runs
        Then a warning is returned; within balance there is no warning
        """
        blanket = self._blanket_order()
        line = self._reference_quotation(blanket).order_line
        line.product_uom_qty = 11.0
        result = line._onchange_qty_blanket_order()
        self.assertIn("exceeds available balance", result["warning"]["message"])
        line.product_uom_qty = 5.0
        self.assertFalse(line._onchange_qty_blanket_order())

    def test_balance_is_shared_between_reference_quotations(self):
        """
        Given a blanket order already consumed by 8 of 10 units
        When another reference quotation asks for 3
        Then it is blocked because only 2 remain
        """
        blanket = self._blanket_order()
        first = self._reference_quotation(blanket)
        first.order_line.product_uom_qty = 8.0
        first.action_confirm()
        second = self._reference_quotation(blanket)
        self.assertEqual(second.order_line.available_bo_qty, 2.0)
        second.order_line.product_uom_qty = 3.0
        with self.assertRaises(ValidationError):
            second.action_confirm()

    # ------------------------------------------------------------------
    # Increment quotation (amendments)
    # ------------------------------------------------------------------
    def test_increment_quotation_is_flagged(self):
        """
        Given an open blanket order
        When the user creates an increment quotation
        Then it is flagged as an amendment with zero quantity lines
        """
        blanket = self._blanket_order()
        quotation = self._increment_quotation(blanket)
        self.assertEqual(quotation.blanket_order_type, "amendment")
        self.assertTrue(quotation.is_blanket_order_increment)
        self.assertEqual(quotation.order_line.product_uom_qty, 0.0)

    def test_confirm_increment_increases_blanket_quantity(self):
        """
        Given an increment quotation of 5 units over a 10 units blanket line
        When it is confirmed
        Then the blanket line grows to 15 and the blanket form is returned
        """
        blanket = self._blanket_order()
        quotation = self._increment_quotation(blanket)
        quotation.order_line.product_uom_qty = 5.0
        action = quotation.action_confirm()
        self.assertEqual(blanket.line_ids.original_uom_qty, 15.0)
        self.assertEqual(blanket.line_ids.remaining_uom_qty, 15.0)
        self.assertEqual(action["res_model"], "sale.blanket.order")
        self.assertEqual(action["res_id"], blanket.id)

    def test_increment_can_reduce_quantity(self):
        """
        Given an increment quotation of minus 4 units over a 10 units line
        When it is confirmed
        Then the blanket line goes down to 6
        """
        blanket = self._blanket_order()
        quotation = self._increment_quotation(blanket)
        quotation.order_line.product_uom_qty = -4.0
        quotation.action_confirm()
        self.assertEqual(blanket.line_ids.original_uom_qty, 6.0)

    def test_increment_cannot_drop_below_zero(self):
        """
        Given an increment quotation of minus 11 units over a 10 units line
        When it is confirmed
        Then a validation error is raised and the line is unchanged
        """
        blanket = self._blanket_order()
        quotation = self._increment_quotation(blanket)
        quotation.order_line.product_uom_qty = -11.0
        with self.assertRaises(ValidationError):
            quotation.action_confirm()
        self.assertEqual(blanket.line_ids.original_uom_qty, 10.0)

    def test_increment_with_new_product_adds_blanket_line(self):
        """
        Given an increment quotation with a new product line
        When it is confirmed
        Then the blanket order receives a new line for that product
        """
        blanket = self._blanket_order()
        quotation = self._increment_quotation(blanket)
        self.env["sale.order.line"].create(
            {
                "order_id": quotation.id,
                "product_id": self.product_2.id,
                "product_uom_qty": 7.0,
                "price_unit": 50.0,
            }
        )
        quotation.action_confirm()
        new_line = blanket.line_ids.filtered(lambda r: r.product_id == self.product_2)
        self.assertEqual(len(new_line), 1)
        self.assertEqual(new_line.original_uom_qty, 7.0)
        self.assertEqual(new_line.price_unit, 50.0)

    # ------------------------------------------------------------------
    # Onchanges / computed fields on the sale order
    # ------------------------------------------------------------------
    def test_selecting_blanket_order_fills_quotation_lines(self):
        """
        Given a blanket order with one line
        When it is selected on a new quotation
        Then the quotation lines are rebuilt from the blanket lines
        """
        blanket = self._blanket_order()
        order = self.env["sale.order"].new(
            {"partner_id": self.partner.id, "blanket_order_id": blanket.id}
        )
        order._onchange_blanket_order_id()
        self.assertEqual(len(order.order_line), 1)
        line = order.order_line
        self.assertEqual(line.product_id, self.product)
        self.assertEqual(line.price_unit, 100.0)
        self.assertEqual(line.product_uom_qty, 0.0)

    def test_product_onchange_binds_blanket_line(self):
        """
        Given a quotation tied to a blanket order
        When a line is set to a product present on the blanket
        Then the line is bound to the blanket line with its price
        """
        blanket = self._blanket_order()
        order = self._quotation()
        order.blanket_order_id = blanket
        line = order.order_line
        line.blanket_order_line_id = False
        line._onchange_product_blanket_order()
        self.assertEqual(line.blanket_order_line_id, blanket.line_ids)
        self.assertEqual(line.price_unit, 100.0)

    def test_quantities_without_blanket_line_are_zero(self):
        """
        Given a sale line not bound to a blanket line
        When the blanket quantities are computed
        Then original and available quantities are zero
        """
        line = self._quotation().order_line
        self.assertEqual(line.original_bo_qty, 0.0)
        self.assertEqual(line.available_bo_qty, 0.0)

    def test_create_blanket_line_from_sale_line(self):
        """
        Given a quotation line without blanket line on a quotation tied to a BO
        When a blanket line is created from it
        Then the blanket order gets a line with the sale line values
        """
        blanket = self._blanket_order()
        order = self._quotation(qty=3.0, price=80.0)
        order.blanket_order_id = blanket
        before = len(blanket.line_ids)
        order.order_line.create_blanket_order_line()
        self.assertEqual(len(blanket.line_ids), before + 1)
        self.assertIn(80.0, blanket.line_ids.mapped("price_unit"))

    def test_line_quantity_change_does_not_reprice(self):
        """
        Given a quotation line whose price was set from the blanket order
        When the quantity/UoM change handler runs
        Then the price is kept (the standard pricelist repricing is disabled)
        """
        blanket = self._blanket_order()
        line = self._reference_quotation(blanket).order_line
        line.price_unit = 77.0
        line.product_uom_change()
        self.assertEqual(line.price_unit, 77.0)

    def test_reference_confirmation_ignores_lines_without_blanket_line(self):
        """
        Given a reference quotation with an extra line not tied to the blanket
        When the balance is validated on confirmation
        Then only blanket lines are checked, so the extra quantity is not blocked
        """
        blanket = self._blanket_order()
        quotation = self._reference_quotation(blanket)
        quotation.order_line.product_uom_qty = 2.0
        self.env["sale.order.line"].create(
            {
                "order_id": quotation.id,
                "product_id": self.product_2.id,
                "product_uom_qty": 99.0,
                "price_unit": 50.0,
            }
        )
        quotation._validate_bo_quantities()
        action = quotation.action_confirm()
        order = self.env["sale.order"].browse(action["res_id"])
        self.assertEqual(order.order_line.product_uom_qty, 2.0)
