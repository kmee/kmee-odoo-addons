# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import io
import re
import zipfile

from odoo.tests.common import TransactionCase, tagged


def _odt_text(content):
    """Visible text of a rendered ODT (content.xml without tags)."""
    xml = zipfile.ZipFile(io.BytesIO(content)).read("content.xml").decode()
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml))


@tagged("post_install", "-at_install")
class TestSaleReportPy3o(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.report = cls.env.ref("l10n_br_sale_report_py3o.action_report_saleorder")
        cls.proforma = cls.env.ref(
            "l10n_br_sale_report_py3o.action_report_pro_forma_invoice"
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Cliente Relatorio LTDA", "lang": "en_US"}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Produto Relatorio", "list_price": 150.0}
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 3,
                            "price_unit": 150.0,
                        },
                    )
                ],
            }
        )

    def _render(self, report):
        report.py3o_filetype = "odt"  # native format: no LibreOffice needed
        content, filetype = report._render_py3o(report.report_name, self.order.ids)
        self.assertEqual(filetype, "odt")
        return _odt_text(content)

    def test_reports_are_registered_as_py3o_on_sale_order(self):
        """
        Given the module is installed
        When the report actions are read
        Then both are py3o reports of sale.order, bound to the model, with the
        ODT template shipped by the module
        """
        for report in (self.report, self.proforma):
            self.assertEqual(report.report_type, "py3o")
            self.assertEqual(report.model, "sale.order")
            self.assertEqual(report.py3o_template_fallback, "report/sale_order.odt")
            self.assertIn(
                report,
                self.env["ir.actions.report"].search([("model", "=", "sale.order")]),
            )
        self.assertEqual(
            self.report.report_name, "l10n_br_sale_report_py3o.report_saleorder"
        )
        self.assertEqual(
            self.proforma.report_name,
            "l10n_br_sale_report_py3o.report_saleorder_pro_forma",
        )

    def test_quotation_renders_order_data(self):
        """
        Given a draft quotation with one line (3 x 150.00)
        When the quotation report is rendered
        Then the text shows it is a Quotation with the order number, the
        product, the unit price and the line subtotal
        """
        text = self._render(self.report)
        self.assertIn("Quotation " + self.order.name, text)
        self.assertIn("Produto Relatorio", text)
        self.assertIn("150.00", text)
        self.assertIn("450.00", text)
        self.assertNotIn("PRO-FORMA", text)
        self.assertNotIn("Order Acknowledgement", text)

    def test_confirmed_order_renders_order_acknowledgement(self):
        """
        Given a confirmed sale order
        When the quotation report is rendered
        Then the document title becomes Order Acknowledgement
        """
        self.order.action_confirm()
        text = self._render(self.report)
        self.assertIn("Order Acknowledgement " + self.order.name, text)
        self.assertNotIn("Quotation " + self.order.name, text)

    def test_cancelled_order_is_marked_canceled(self):
        """
        Given a cancelled order
        When the report is rendered
        Then the title carries the canceled marker
        """
        self.order.action_cancel()
        text = self._render(self.report)
        self.assertIn("canceled", text)
        self.assertIn(self.order.name, text)

    def test_pro_forma_report_renders_pro_forma_title(self):
        """
        Given a draft quotation
        When the pro-forma report is rendered
        Then the title is PRO-FORMA Invoice, not Quotation
        """
        text = self._render(self.proforma)
        self.assertIn("PRO-FORMA Invoice " + self.order.name, text)
        self.assertNotIn("Quotation " + self.order.name, text)

    def test_partner_without_language_gets_brazilian_titles(self):
        """
        Given a customer without language
        When the quotation and pro-forma reports are rendered
        Then the titles are Portuguese (the template falls back to pt_BR)
        """
        self.partner.lang = False
        text = self._render(self.report)
        self.assertIn("Cota\u00e7\u00e3o " + self.order.name, text)
        text = self._render(self.proforma)
        self.assertIn("Fatura Pro-Forma " + self.order.name, text)

    def test_download_file_names(self):
        """
        Given a quotation of customer 'Cliente Relatorio LTDA'
        When the download names are computed
        Then the quotation is '<order>-<date>-<customer>.pdf' and the pro-forma
        is 'Proforma-<order>-<customer>.pdf', spaces replaced by underscores
        """
        name = self.report.gen_report_download_filename(self.order.ids, {})
        self.assertTrue(name.startswith(self.order.name + "-"))
        self.assertTrue(name.endswith("-Cliente_Relatorio_LTDA.pdf"))
        self.assertEqual(
            self.proforma.gen_report_download_filename(self.order.ids, {}),
            "Proforma-%s-Cliente_Relatorio_LTDA.pdf" % self.order.name,
        )
