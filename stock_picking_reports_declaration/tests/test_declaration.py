# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeclaration(TransactionCase):
    def test_layout_wizard_writes_company_declaration(self):
        company = self.env.company
        wizard = self.env["base.document.layout"].create({})
        wizard.declaration_receipt = "<p>I received the goods.</p>"
        self.assertIn("I received the goods.", company.declaration_receipt)

    def test_report_templates_extended(self):
        for xmlid in (
            "stock_picking_reports_declaration.report_picking_declaration",
            "stock_picking_reports_declaration.report_delivery_document_declaration",
        ):
            view = self.env.ref(xmlid)
            self.assertIn("declaration_receipt", view.arch_db)
