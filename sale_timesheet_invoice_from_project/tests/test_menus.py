# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestProjectInvoiceMenus(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.menu_invoice = cls.env.ref(
            "sale_timesheet_invoice_from_project.menu_project_create_invoice"
        )
        cls.menu_order = cls.env.ref(
            "sale_timesheet_invoice_from_project.menu_project_create_sale_order"
        )
        base = "base.group_user,"
        users = {
            "plain": "",
            "project_manager": "project.group_project_manager",
            "salesman": "sales_team.group_sale_salesman",
            "accountant": "account.group_account_invoice",
            "manager_salesman": "project.group_project_manager,"
            "sales_team.group_sale_salesman",
            "accountant_all_leads": "account.group_account_invoice,"
            "sales_team.group_sale_salesman_all_leads",
            "manager_all_leads": "project.group_project_manager,"
            "sales_team.group_sale_salesman_all_leads",
        }
        cls.users = {
            key: new_test_user(
                cls.env, login="tsheet_%s" % key, groups=(base + groups).rstrip(",")
            )
            for key, groups in users.items()
        }

    def _visible_menus(self, user):
        return self.env["ir.ui.menu"].with_user(user)._visible_menu_ids()

    def test_menus_live_under_project_configuration(self):
        """
        Given the menus created by the module
        When we read their parent
        Then both are entries of the Project > Configuration menu
        """
        parent = self.env.ref("project.menu_project_config")
        self.assertEqual(self.menu_invoice.parent_id, parent)
        self.assertEqual(self.menu_order.parent_id, parent)

    def test_menus_actions_open_the_sale_timesheet_wizards(self):
        """
        Given the two menus
        When we read their actions
        Then they open the create invoice and create sales order wizards as dialogs
        for the project model
        """
        invoice = self.menu_invoice.action
        order = self.menu_order.action
        self.assertEqual(invoice.res_model, "project.create.invoice")
        self.assertEqual(order.res_model, "project.create.sale.order")
        for action in (invoice, order):
            self.assertEqual(action.target, "new")
            self.assertIn("project.project", action.context)

    def test_create_invoice_menu_needs_group_and_wizard_access(self):
        """
        Given the Create Invoice menu (accountants and project managers) whose
        wizard model is only accessible to salesmen with all leads
        When different users list their visible menus
        Then it shows only for users that satisfy both the menu groups and the
        wizard access, and stays hidden for users that miss either one
        """
        visible = {
            k: self.menu_invoice.id in self._visible_menus(u)
            for k, u in self.users.items()
        }
        self.assertTrue(visible["accountant_all_leads"])
        self.assertTrue(visible["manager_all_leads"])
        self.assertFalse(visible["plain"])
        self.assertFalse(visible["salesman"])
        # menu group ok but no access to the wizard model
        self.assertFalse(visible["accountant"])
        self.assertFalse(visible["project_manager"])

    def test_create_sale_order_menu_needs_group_and_wizard_access(self):
        """
        Given the Create Sales Order menu (salesmen and project managers) whose
        wizard model is only accessible to salesmen
        When different users list their visible menus
        Then it shows only for users that satisfy both the menu groups and the
        wizard access, and stays hidden for users that miss either one
        """
        visible = {
            k: self.menu_order.id in self._visible_menus(u)
            for k, u in self.users.items()
        }
        self.assertTrue(visible["salesman"])
        self.assertTrue(visible["manager_salesman"])
        self.assertTrue(visible["manager_all_leads"])
        self.assertFalse(visible["plain"])
        self.assertFalse(visible["accountant"])
        # menu group ok but no access to the wizard model
        self.assertFalse(visible["project_manager"])

    def _billable_project(self):
        partner = self.env["res.partner"].create({"name": "Customer"})
        product = self.env["product.product"].create(
            {
                "name": "Billable service",
                "type": "service",
                "invoice_policy": "order",
                "service_tracking": "no",
            }
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 3.0})
                ],
            }
        )
        order.action_confirm()
        project = self.env["project.project"].create({"name": "Billable project"})
        self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": project.id,
                "sale_line_id": order.order_line.id,
            }
        )
        return project, order

    def test_invoice_action_runs_the_wizard_for_the_project(self):
        """
        Given a project whose task is linked to a confirmed sale order line
        When the Create Invoice action is opened from the project and confirmed
        Then the wizard proposes the order and leads to the advance payment wizard
        """
        project, order = self._billable_project()
        action = self.menu_invoice.action
        wizard = (
            self.env[action.res_model]
            .with_context(active_model="project.project", active_id=project.id)
            .create({"sale_order_id": order.id})
        )
        self.assertEqual(wizard.project_id, project)
        self.assertEqual(wizard._candidate_orders, order)
        result = wizard.action_create_invoice()
        self.assertEqual(result["res_model"], "sale.advance.payment.inv")
        self.assertEqual(result["context"]["active_ids"], order.ids)

    def test_wizard_refuses_to_run_outside_a_project(self):
        """
        Given the Create Invoice action
        When it is opened without the project context
        Then the sale_timesheet wizard refuses with a UserError
        """
        action = self.menu_invoice.action
        with self.assertRaises(UserError):
            self.env[action.res_model].with_context(active_model="sale.order").create(
                {}
            )
