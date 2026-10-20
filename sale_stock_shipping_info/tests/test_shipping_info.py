# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from contextlib import ExitStack
from unittest.mock import patch

from lxml import etree

from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleStockShippingInfo(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.heavy = cls.env["product.product"].create(
            {
                "name": "Heavy",
                "type": "consu",
                "is_storable": True,
                "weight": 2.0,
                "volume": 0.5,
            }
        )
        cls.light = cls.env["product.product"].create(
            {
                "name": "Light",
                "type": "consu",
                "is_storable": True,
                "weight": 0.25,
                "volume": 0.1,
            }
        )
        cls.uom_dozen = cls.env.ref("uom.product_uom_dozen")
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")

    def _order(self, lines):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [(0, 0, vals) for vals in lines],
            }
        )

    def test_empty_order_has_zero_weight_and_volume(self):
        """
        Given an order without lines
        When the shipping info is read
        Then weight and volume are zero
        """
        order = self._order([])
        self.assertEqual(order.shipping_weight, 0.0)
        self.assertEqual(order.shipping_volume, 0.0)

    def test_weight_and_volume_are_summed_over_lines(self):
        """
        Given an order with 3 Heavy (2kg, 0.5 m3) and 4 Light (0.25kg, 0.1 m3)
        When the shipping info is read
        Then weight is 3*2 + 4*0.25 and volume is 3*0.5 + 4*0.1
        """
        order = self._order(
            [
                {"product_id": self.heavy.id, "product_uom_qty": 3.0},
                {"product_id": self.light.id, "product_uom_qty": 4.0},
            ]
        )
        self.assertAlmostEqual(order.shipping_weight, 7.0)
        self.assertAlmostEqual(order.shipping_volume, 1.9)

    def test_quantity_is_converted_to_product_uom(self):
        """
        Given a line of 2 dozens of a product weighing 0.25 kg and 0.1 m3 per unit
        When the shipping info is read
        Then 24 units are considered, not 2
        """
        order = self._order(
            [
                {
                    "product_id": self.light.id,
                    "product_uom": self.uom_dozen.id,
                    "product_uom_qty": 2.0,
                }
            ]
        )
        self.assertAlmostEqual(order.shipping_weight, 6.0)
        self.assertAlmostEqual(order.shipping_volume, 2.4)

    def test_section_note_and_zero_quantity_lines_are_ignored(self):
        """
        Given an order with a section, a note and a zero quantity line
        When the shipping info is read
        Then only the line with quantity counts
        """
        order = self._order(
            [
                {"display_type": "line_section", "name": "Section"},
                {"display_type": "line_note", "name": "Note"},
                {"product_id": self.light.id, "product_uom_qty": 0.0},
                {"product_id": self.heavy.id, "product_uom_qty": 1.0},
            ]
        )
        self.assertAlmostEqual(order.shipping_weight, 2.0)
        self.assertAlmostEqual(order.shipping_volume, 0.5)

    def test_totals_follow_line_changes(self):
        """
        Given an order with totals computed
        When quantity, uom and product of the line change, and a line is removed
        Then the stored totals are recomputed each time
        """
        order = self._order([{"product_id": self.heavy.id, "product_uom_qty": 1.0}])
        self.assertAlmostEqual(order.shipping_weight, 2.0)
        order.order_line.product_uom_qty = 5.0
        self.assertAlmostEqual(order.shipping_weight, 10.0)
        order.order_line.product_id = self.light
        self.assertAlmostEqual(order.shipping_weight, 1.25)
        order.order_line.product_uom = self.uom_dozen
        self.assertAlmostEqual(order.shipping_weight, 15.0)
        order.order_line.unlink()
        self.assertEqual(order.shipping_weight, 0.0)
        self.assertEqual(order.shipping_volume, 0.0)

    def test_totals_are_stored_and_searchable(self):
        """
        Given a heavy order and a light order
        When searching orders by shipping weight
        Then the stored field filters them correctly
        """
        heavy_order = self._order(
            [{"product_id": self.heavy.id, "product_uom_qty": 10.0}]
        )
        light_order = self._order(
            [{"product_id": self.light.id, "product_uom_qty": 1.0}]
        )
        found = self.env["sale.order"].search(
            [("id", "in", (heavy_order | light_order).ids), ("shipping_weight", ">", 5)]
        )
        self.assertEqual(found, heavy_order)

    def test_form_shows_totals_for_new_lines(self):
        """
        Given the sale order form
        When a line is added through the form
        Then weight and volume are computed on screen
        """
        with Form(self.env["sale.order"]) as form:
            form.partner_id = self.partner
            with form.order_line.new() as line:
                line.product_id = self.heavy
                line.product_uom_qty = 2.0
            self.assertAlmostEqual(form.shipping_weight, 4.0)
            self.assertAlmostEqual(form.shipping_volume, 1.0)

    def test_unit_names_follow_system_parameters(self):
        """
        Given the weight and volume unit system parameters
        When they are switched between metric and imperial
        Then the unit names shown beside the totals follow them
        """
        order = self._order([])
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("product.weight_in_lbs", "0")
        params.set_param("product.volume_in_cubic_feet", "0")
        metric = order.weight_uom_name, order.volume_uom_name
        self.assertEqual(metric[0].lower(), "kg")
        self.assertIn("m", metric[1])
        params.set_param("product.weight_in_lbs", "1")
        params.set_param("product.volume_in_cubic_feet", "1")
        order.invalidate_recordset(["weight_uom_name", "volume_uom_name"])
        imperial = order.weight_uom_name, order.volume_uom_name
        self.assertEqual(imperial[0].lower(), "lb")
        self.assertIn("ft", imperial[1])

    def test_dimension_unit_name_is_meter(self):
        """
        Given the uom meter of the base data
        When the dimension unit name is read
        Then it is the name of the meter uom
        """
        order = self._order([])
        meter = self.env.ref("uom.product_uom_meter")
        self.assertEqual(order.dimension_uom_name, meter.name)

    def test_longest_dimension_is_manual_input(self):
        """
        Given the longest dimension typed by the user
        When the order lines change
        Then the typed value is kept (current behavior: the field is not computed)
        """
        order = self._order([{"product_id": self.heavy.id, "product_uom_qty": 1.0}])
        order.longest_dimension = 2.5
        order.order_line.product_uom_qty = 3.0
        self.assertEqual(order.longest_dimension, 2.5)

    def _patch_dimensions(self, dimensions):
        """Emulate the optional product dimension fields (not a dependency).

        :param dimensions: {product id: (length, height, width)} in centimeters
        """
        product_model = type(self.env["product.product"])
        centimeter = self.env.ref("uom.product_uom_cm")

        def getter(index):
            return property(lambda rec: dimensions.get(rec.id, (0.0, 0.0, 0.0))[index])

        stack = ExitStack()
        for name, value in (
            ("dimensional_uom_id", property(lambda rec: centimeter)),
            ("product_length", getter(0)),
            ("product_height", getter(1)),
            ("product_width", getter(2)),
        ):
            stack.enter_context(patch.object(product_model, name, value, create=True))
        return stack

    def test_longest_dimension_is_detected_from_product_dimensions(self):
        """
        Given products with dimensions in centimeters (150x20x10 and 30x40x50)
        When both are sold in the same order
        Then the longest dimension is the biggest one converted to meters (1.5)
        """
        dimensions = {self.heavy.id: (150.0, 20.0, 10.0), self.light.id: (30, 40, 50)}
        with self._patch_dimensions(dimensions):
            order = self._order(
                [
                    {"product_id": self.heavy.id, "product_uom_qty": 1.0},
                    {"product_id": self.light.id, "product_uom_qty": 1.0},
                ]
            )
            order.flush_recordset()
            self.assertAlmostEqual(order.longest_dimension, 1.5)

    def test_longest_dimension_ignores_products_without_dimensions(self):
        """
        Given a product without dimensions and one measuring 80 cm
        When the order contains only the product without dimensions, then both
        Then the longest dimension is 0 and then 0.8
        """
        with self._patch_dimensions({self.light.id: (80.0, 10.0, 10.0)}):
            order = self._order([{"product_id": self.heavy.id, "product_uom_qty": 1}])
            order.flush_recordset()
            self.assertEqual(order.longest_dimension, 0.0)
            self.env["sale.order.line"].create(
                {
                    "order_id": order.id,
                    "product_id": self.light.id,
                    "product_uom_qty": 1.0,
                }
            )
            order.flush_recordset()
            self.assertAlmostEqual(order.longest_dimension, 0.8)

    def test_form_view_has_shipping_group(self):
        """
        Given the sale order form view
        When it is loaded
        Then the shipping information group sits in the Other Info tab
        """
        arch = self.env["sale.order"].get_view(
            self.env.ref("sale.view_order_form").id, "form"
        )["arch"]
        root = etree.fromstring(arch)
        names = root.xpath(
            "//page[@name='other_information']"
            "//group[@name='sale_shipping_info']//field/@name"
        )
        self.assertEqual(
            names,
            [
                "shipping_weight",
                "weight_uom_name",
                "shipping_volume",
                "volume_uom_name",
                "longest_dimension",
                "dimension_uom_name",
            ],
        )
