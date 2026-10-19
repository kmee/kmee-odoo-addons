# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectInvoiceAction(TransactionCase):
    def test_create_invoice_server_action(self):
        action = self.env.ref(
            "sale_timesheet_invoice_from_project."
            "project_project_action_multi_create_invoice"
        )
        self.assertEqual(action.binding_model_id.model, "project.project")
        self.assertEqual(action.state, "code")

    def test_action_opens_invoice_wizard_for_project_orders(self):
        partner = self.env["res.partner"].create({"name": "Invoice Partner"})
        product = self.env["product.product"].create(
            {"name": "Service", "type": "service"}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 1.0})
                ],
            }
        )
        project = self.env["project.project"].create(
            {
                "name": "Project to invoice",
                "sale_line_id": order.order_line.id,
            }
        )
        action = project.action_create_invoice_from_projects()
        self.assertEqual(action["res_model"], "sale.advance.payment.inv")
        self.assertEqual(action["context"]["active_ids"], order.ids)
        self.assertEqual(action["context"]["active_id"], order.id)
