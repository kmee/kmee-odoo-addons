# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime

import lxml.html

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectNumber(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create(
            {"name": "Test project", "zitron_project_number": "70.000.099"}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Vendor"})
        cls.user = cls.env["res.users"].create(
            {
                "name": "Buyer",
                "login": "hd1801_buyer",
                "phone": "(11) 94455-6431",
            }
        )
        cls.po = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "project_id": cls.project.id,
                "user_id": cls.user.id,
            }
        )

    def test_search_by_number(self):
        found = self.env["project.project"].search(
            [("zitron_project_number", "=", "70.000.099")]
        )
        self.assertEqual(found, self.project)

    def test_pdf_html_has_number_phone_and_label(self):
        html = (
            self.env["ir.actions.report"]
            ._render_qweb_html("purchase.report_purchaseorder", self.po.ids)[0]
            .decode()
        )
        self.assertIn("70.000.099", html)
        self.assertIn("94455-6431", html)
        self.assertNotIn("desta OC", html)


@tagged("post_install", "-at_install")
class TestDeliveryDate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Vendor"})
        cls.product = cls.env["product.product"].create({"name": "Part X"})
        cls.date_order = datetime(2026, 11, 10, 14, 0, 0)
        cls.po = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "date_order": cls.date_order,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_qty": 1,
                            "price_unit": 10,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_qty": 2,
                            "price_unit": 10,
                            # same day as the order, different time of day
                            "date_planned": datetime(2026, 11, 10, 20, 0, 0),
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_qty": 3,
                            "price_unit": 10,
                            "date_planned": datetime(2026, 11, 25, 12, 0, 0),
                        }
                    ),
                ],
            }
        )
        cls.line_default, cls.line_same_day, cls.line_later = cls.po.order_line

    def _delivery_cells(self):
        html = self.env["ir.actions.report"]._render_qweb_html(
            "purchase.report_purchaseorder", self.po.ids
        )[0]
        root = lxml.html.fromstring(html)
        return [
            "".join(td.itertext()).strip()
            for td in root.xpath("//td[@name='td_date_planned']")
        ]

    def test_default_date_is_not_informed(self):
        self.assertEqual(self.line_default.date_planned, self.date_order)
        self.assertFalse(self.line_default._zitron_delivery_informed())
        self.assertTrue(self.line_same_day._zitron_delivery_informed())
        self.assertTrue(self.line_later._zitron_delivery_informed())

    def test_pdf_delivery_column(self):
        cells = self._delivery_cells()
        self.assertEqual(len(cells), 3)
        self.assertEqual(cells[0], "")
        self.assertIn("2026", cells[1])
        self.assertIn("2026", cells[2])
        self.assertIn("25", cells[2])
