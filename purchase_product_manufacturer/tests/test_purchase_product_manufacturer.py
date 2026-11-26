# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseProductManufacturer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.order = cls.env.ref("purchase_product_manufacturer.purchase_order_pecas")
        cls.line = cls.env.ref(
            "purchase_product_manufacturer.purchase_order_line_parafuso"
        )

    def test_line_manufacturer_fields(self):
        product = self.line.product_id
        self.assertEqual(self.line.manufacturer, product.manufacturer_id)
        self.assertEqual(self.line.manufacturer_pref, "MSA-4410-B")
        self.assertEqual(self.line.manufacturer_pname, product.manufacturer_pname)
        self.assertEqual(self.line.manufacturer_purl, product.manufacturer_purl)
        product.manufacturer_pref = "MSA-4410-C"
        self.assertEqual(self.line.manufacturer_pref, "MSA-4410-C")

    def test_reports_show_manufacturer_and_part_number(self):
        for report in (
            "purchase.report_purchasequotation",
            "purchase.report_purchaseorder",
        ):
            html = (
                self.env["ir.actions.report"]
                ._render_qweb_html(report, self.order.ids)[0]
                .decode()
            )
            self.assertIn("Manufacturer/PartNumber", html)
            self.assertIn("Metalúrgica Serra Azul", html)
            self.assertIn("MSA-4410-B", html)
