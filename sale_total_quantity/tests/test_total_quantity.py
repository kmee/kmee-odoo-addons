# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleTotalQuantity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.product_a = cls.env["product.product"].create({"name": "Product A"})
        cls.product_b = cls.env["product.product"].create({"name": "Product B"})

    def _order(self, lines=()):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [(0, 0, vals) for vals in lines],
            }
        )

    def test_empty_order_has_zero_totals(self):
        """
        Given an order without lines
        When the totals are read
        Then both are zero
        """
        order = self._order()
        self.assertEqual(order.total_sale_product, 0)
        self.assertEqual(order.total_sale_quantity, 0.0)

    def test_totals_sum_quantities_and_count_distinct_products(self):
        """
        Given an order with 2 lines of product A and 1 line of product B
        When the totals are read
        Then the quantity is the sum of all lines and products are counted once
        """
        order = self._order(
            [
                {"product_id": self.product_a.id, "product_uom_qty": 2.0},
                {"product_id": self.product_a.id, "product_uom_qty": 3.5},
                {"product_id": self.product_b.id, "product_uom_qty": 4.0},
            ]
        )
        self.assertEqual(order.total_sale_product, 2)
        self.assertEqual(order.total_sale_quantity, 9.5)

    def test_section_and_note_lines_are_not_counted(self):
        """
        Given an order with one product line, a section and a note
        When the totals are read
        Then only the product line counts
        """
        order = self._order(
            [
                {"display_type": "line_section", "name": "Section"},
                {"product_id": self.product_a.id, "product_uom_qty": 5.0},
                {"display_type": "line_note", "name": "Note"},
            ]
        )
        self.assertEqual(order.total_sale_product, 1)
        self.assertEqual(order.total_sale_quantity, 5.0)

    def test_totals_follow_line_changes(self):
        """
        Given an order with totals already computed
        When a line quantity changes, a line is added and a line is removed
        Then the totals are recomputed every time
        """
        order = self._order([{"product_id": self.product_a.id, "product_uom_qty": 1}])
        self.assertEqual(order.total_sale_quantity, 1.0)
        order.order_line.product_uom_qty = 6.0
        self.assertEqual(order.total_sale_quantity, 6.0)
        line_b = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product_b.id,
                "product_uom_qty": 2.0,
            }
        )
        self.assertEqual(order.total_sale_product, 2)
        self.assertEqual(order.total_sale_quantity, 8.0)
        line_b.unlink()
        self.assertEqual(order.total_sale_product, 1)
        self.assertEqual(order.total_sale_quantity, 6.0)

    def test_totals_follow_product_change_on_line(self):
        """
        Given two lines of the same product
        When one line is switched to another product
        Then the distinct product count goes from 1 to 2
        """
        order = self._order(
            [
                {"product_id": self.product_a.id, "product_uom_qty": 1.0},
                {"product_id": self.product_a.id, "product_uom_qty": 1.0},
            ]
        )
        self.assertEqual(order.total_sale_product, 1)
        order.order_line[1].product_id = self.product_b
        self.assertEqual(order.total_sale_product, 2)

    def test_totals_are_computed_per_order_in_a_recordset(self):
        """
        Given two orders with different lines
        When the totals are read from the joint recordset
        Then each order has its own totals
        """
        order1 = self._order([{"product_id": self.product_a.id, "product_uom_qty": 1}])
        order2 = self._order(
            [
                {"product_id": self.product_a.id, "product_uom_qty": 10},
                {"product_id": self.product_b.id, "product_uom_qty": 20},
            ]
        )
        self.assertEqual((order1 | order2).mapped("total_sale_quantity"), [1.0, 30.0])
        self.assertEqual((order1 | order2).mapped("total_sale_product"), [1, 2])

    def test_form_shows_live_totals(self):
        """
        Given the sale order form
        When lines are added through the form
        Then the totals update on screen before saving
        """
        with Form(self.env["sale.order"]) as form:
            form.partner_id = self.partner
            with form.order_line.new() as line:
                line.product_id = self.product_a
                line.product_uom_qty = 3
            with form.order_line.new() as line:
                line.product_id = self.product_b
                line.product_uom_qty = 4
            self.assertEqual(form.total_sale_product, 2)
            self.assertEqual(form.total_sale_quantity, 7.0)

    def test_form_view_has_totals_group(self):
        """
        Given the sale order form view
        When it is loaded
        Then the totals group with both fields is rendered before the note group
        """
        arch = self.env["sale.order"].get_view(
            self.env.ref("sale.view_order_form").id, "form"
        )["arch"]
        root = etree.fromstring(arch)
        names = root.xpath("//group[@name='total']/field/@name")
        self.assertEqual(names, ["total_sale_product", "total_sale_quantity"])
