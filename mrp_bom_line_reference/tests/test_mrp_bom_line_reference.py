# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestMrpBomLineReference(TransactionCase):
    def test_manufacturer_fields_come_from_product(self):
        line = self.env.ref("mrp_bom_line_reference.mrp_bom_line_resistor")
        product = line.product_id
        self.assertTrue(line.manufacturer_id)
        self.assertEqual(line.manufacturer_id, product.manufacturer_id)
        self.assertEqual(line.manufacturer_pname, product.manufacturer_pname)
        self.assertEqual(line.manufacturer_pref, product.manufacturer_pref)

    def test_zero_quantity_is_forbidden(self):
        line = self.env.ref("mrp_bom_line_reference.mrp_bom_line_resistor")
        with self.assertRaises(ValidationError):
            line.product_qty = 0
