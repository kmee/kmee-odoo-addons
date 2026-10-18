# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectInvoiceMenu(TransactionCase):
    def test_create_invoice_action_and_menu(self):
        action = self.env.ref(
            "sale_timesheet_invoice_from_project."
            "project_project_action_multi_create_invoice"
        )
        self.assertEqual(action.res_model, "project.create.invoice")
        menu = self.env.ref(
            "sale_timesheet_invoice_from_project.menu_project_create_invoice"
        )
        self.assertEqual(menu.action, action)
        self.assertEqual(menu.parent_id, self.env.ref("project.menu_project_config"))
