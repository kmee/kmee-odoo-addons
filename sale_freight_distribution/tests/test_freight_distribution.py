# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFreightDistribution(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, no_reset_password=True)
        )
        cls.env.company.delivery_costs = "total"
        cls.partner = cls.env["res.partner"].create({"name": "Freight Customer"})
        Product = cls.env["product.product"]
        cls.prod_a = Product.create(
            {"name": "Freight A", "type": "product", "list_price": 100.0}
        )
        cls.prod_b = Product.create(
            {"name": "Freight B", "type": "product", "list_price": 100.0}
        )
        cls.service = Product.create(
            {"name": "Freight Service", "type": "service", "list_price": 500.0}
        )

    def _order(self, lines):
        """lines: list of (product, qty, price)"""
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "price_unit": price,
                        },
                    )
                    for product, qty, price in lines
                ],
            }
        )

    def test_freight_split_proportionally_to_subtotal(self):
        """
        Given an order with two storable lines of 100 and 300
        When the order freight is set to 40
        Then the lines get 10 and 30 (proportional to their subtotals)
        """
        order = self._order([(self.prod_a, 1, 100.0), (self.prod_b, 1, 300.0)])
        order.amount_freight_value = 40.0
        line_a, line_b = order.order_line
        self.assertAlmostEqual(line_a.freight_value, 10.0)
        self.assertAlmostEqual(line_b.freight_value, 30.0)

    def test_service_lines_get_no_freight(self):
        """
        Given an order with a storable line and a service line
        When the order freight is set
        Then the whole freight goes to the storable line, none to the service
        """
        order = self._order([(self.prod_a, 1, 100.0), (self.service, 1, 500.0)])
        order.amount_freight_value = 50.0
        product_line, service_line = order.order_line
        self.assertAlmostEqual(product_line.freight_value, 50.0)
        self.assertEqual(service_line.freight_value, 0.0)

    def test_freight_redistributed_when_order_changes(self):
        """
        Given an order with freight already distributed
        When another storable line is added by writing the order
        Then the freight is spread again including the new line
        """
        order = self._order([(self.prod_a, 1, 100.0)])
        order.amount_freight_value = 40.0
        self.assertAlmostEqual(order.order_line.freight_value, 40.0)
        order.write(
            {
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.prod_b.id,
                            "product_uom_qty": 1,
                            "price_unit": 100.0,
                        },
                    )
                ]
            }
        )
        self.assertEqual(len(order.order_line), 2)
        for line in order.order_line:
            self.assertAlmostEqual(line.freight_value, 20.0)

    def test_freight_redistributed_when_line_removed(self):
        """
        Given an order with freight shared by two storable lines
        When one line is deleted
        Then the remaining line receives all the freight
        """
        order = self._order([(self.prod_a, 1, 100.0), (self.prod_b, 1, 100.0)])
        order.amount_freight_value = 40.0
        first, second = order.order_line
        self.assertAlmostEqual(first.freight_value, 20.0)
        first.unlink()
        self.assertAlmostEqual(second.freight_value, 40.0)

    def test_no_freight_leaves_lines_untouched(self):
        """
        Given an order without freight
        When it is saved
        Then no freight is assigned to the lines
        """
        order = self._order([(self.prod_a, 1, 100.0)])
        order.write({"note": "no freight here"})
        self.assertEqual(order.order_line.freight_value, 0.0)

    def test_order_without_storable_lines_is_skipped(self):
        """
        Given an order with only a service line and a freight value
        When the order is saved
        Then nothing is distributed and no error is raised
        """
        order = self._order([(self.service, 1, 500.0)])
        order.amount_freight_value = 30.0
        self.assertEqual(order.order_line.freight_value, 0.0)

    def test_order_without_lines_is_skipped(self):
        """
        Given an order without any line
        When it is saved
        Then the distribution is skipped without error
        """
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        order.write({"note": "empty"})
        self.assertFalse(order.order_line)

    def test_freight_with_quantity_greater_than_one(self):
        """
        Given a storable line of 3 units (subtotal 300) and a 60 freight
        When the freight is distributed
        Then the sum of the line freights equals the order freight
        """
        order = self._order([(self.prod_a, 3, 100.0)])
        order.amount_freight_value = 60.0
        self.assertAlmostEqual(sum(order.order_line.mapped("freight_value")), 60.0)
