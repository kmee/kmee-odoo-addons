# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseReportHideDate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.view = cls.env.ref("purchase_report_hide_date.purchase_report_hide_date")
        partner = cls.env["res.partner"].create({"name": "Vendor"})
        product = cls.env["product.product"].create(
            {"name": "Report Product", "supplier_taxes_id": [(5, 0, 0)]}
        )
        cls.order = cls.env["purchase.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": 2,
                            "price_unit": 10,
                            "date_planned": "2031-07-22 12:00:00",
                            "tax_ids": [(5, 0, 0)],
                        },
                    )
                ],
            }
        )

    def _render(self):
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(
            "purchase.report_purchaseorder", self.order.ids
        )
        return html.decode()

    def test_report_hides_planned_date_column_and_value(self):
        """
        Given a purchase order line planned for 2031-07-22
        When the standard purchase order report is rendered
        Then neither the "Expected Arrival" block nor the planned date appear
        """
        html = self._render()
        self.assertIn("Report Product", html)
        self.assertNotIn("Expected Arrival", html)
        self.assertNotIn("07/22/2031", html)

    def test_report_shows_date_when_module_view_is_disabled(self):
        """
        Given the same order
        When the module inheriting view is deactivated
        Then the report shows the "Expected Arrival" block and the planned date again
        """
        self.view.active = False
        html = self._render()
        self.assertIn("Expected Arrival", html)
        self.assertIn("07/22/2031", html)

    def test_other_columns_are_kept(self):
        """
        Given the rendered report with the module active
        When we read its table
        Then description, quantity, unit price and amount are still there
        """
        html = self._render()
        for header in ("Description", "Qty", "Unit Price", "Amount"):
            self.assertIn(header, html)

    def test_view_inherits_the_report_document(self):
        """
        Given the view added by the module
        When we read its parent
        Then it extends the standard purchase order document template
        """
        self.assertEqual(
            self.view.inherit_id, self.env.ref("purchase.report_purchaseorder_document")
        )
