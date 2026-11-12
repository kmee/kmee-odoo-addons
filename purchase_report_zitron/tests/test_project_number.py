# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

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
        html = self.env["ir.actions.report"]._render_qweb_html(
            "purchase.report_purchaseorder", self.po.ids
        )[0].decode()
        self.assertIn("70.000.099", html)
        self.assertIn("94455-6431", html)
        self.assertNotIn("desta OC", html)
