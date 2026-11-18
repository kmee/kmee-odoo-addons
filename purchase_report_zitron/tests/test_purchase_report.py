# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Report Test Company"})
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                allowed_company_ids=[cls.company.id],
            )
        )
        cls.partner = cls.env["res.partner"].create({"name": "Vendor"})
        cls.product = cls.env["product.product"].create({"name": "Part X"})
        cls.po = (
            cls.env["purchase.order"]
            .with_company(cls.company)
            .create(
                {
                    "partner_id": cls.partner.id,
                    "company_id": cls.company.id,
                    "order_line": [
                        (
                            0,
                            0,
                            {
                                "product_id": cls.product.id,
                                "name": "Part X",
                                "product_qty": 2,
                                "price_unit": 10.0,
                            },
                        )
                    ],
                }
            )
        )

    def _render(self, report_ref):
        return (
            self.env["ir.actions.report"]
            ._render_qweb_html(report_ref, self.po.ids)[0]
            .decode()
        )

    def test_footer_note_default_is_empty(self):
        self.assertFalse(self.company.purchase_report_footer_note)

    def test_render_purchase_order(self):
        html = self._render("purchase.report_purchaseorder")
        self.assertIn("Part X", html)
        self.assertNotIn("Custom billing note", html)

    def test_render_quotation_wrappers(self):
        for ref in (
            "purchase_report_zitron.report_purchasequotation_zitron",
            "purchase_report_zitron.report_purchasequotation_zitron_portrait",
            "purchase_report_zitron.report_purchaseorder_portrait",
        ):
            with self.subTest(report=ref):
                self.assertIn("Part X", self._render(ref))

    def test_footer_note_rendered_when_configured(self):
        self.company.purchase_report_footer_note = "<p>Custom billing note</p>"
        html = self._render("purchase.report_purchaseorder")
        self.assertIn("Custom billing note", html)
