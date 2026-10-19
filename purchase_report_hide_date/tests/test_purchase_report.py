# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseReportHideDate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env["res.partner"].create({"name": "Vendor"})
        cls.product = cls.env["product.product"].create({"name": "Report Product"})
        cls.order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_qty": 2,
                            "price_unit": 10,
                            "date_planned": "2026-06-15 12:00:00",
                        },
                    )
                ],
            }
        )

    def test_report_hides_expected_arrival(self):
        html = self.env["ir.actions.report"]._render_qweb_html(
            "purchase.report_purchaseorder", self.order.ids
        )[0]
        text = html.decode()
        self.assertIn("Report Product", text)
        self.assertNotIn("Expected Arrival", text)

    def test_inherited_view_is_active(self):
        view = self.env.ref("purchase_report_hide_date.purchase_report_hide_date")
        self.assertEqual(
            view.inherit_id, self.env.ref("purchase.report_purchaseorder_document")
        )
