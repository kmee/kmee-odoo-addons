# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.modules.module import get_manifest
from odoo.tests.common import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountMoveStockCreate(AccountTestInvoicingCommon):
    """The module is a glue: it must come installed together with
    account_move_picking_match_or_create and expose the invoice -> picking
    creation flow that the v14 module provided."""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Glue Product", "detailed_type": "product", "list_price": 10.0}
        )

    def _invoice(self, move_type="out_invoice", qty=4.0):
        return self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": self.partner_a.id,
                "invoice_date": "2024-03-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "quantity": qty,
                            "price_unit": 10.0,
                        },
                    )
                ],
            }
        )

    def test_manifest_is_auto_install_glue_of_match_or_create(self):
        """Given the manifest, Then the module is a glue that auto-installs
        once account_move_picking_match_or_create is available."""
        manifest = get_manifest("account_move_stock_create")
        self.assertTrue(manifest["auto_install"])
        self.assertEqual(manifest["depends"], ["account_move_picking_match_or_create"])

    def test_glue_and_dependency_are_installed_together(self):
        """Given a database with the dependency installed, Then the glue is
        installed too (auto_install worked)."""
        modules = self.env["ir.module.module"].search(
            [
                (
                    "name",
                    "in",
                    [
                        "account_move_stock_create",
                        "account_move_picking_match_or_create",
                    ],
                )
            ]
        )
        self.assertEqual(len(modules), 2)
        self.assertEqual(set(modules.mapped("state")), {"installed"})

    def test_customer_invoice_creates_outgoing_picking(self):
        """Given a customer invoice with a stockable line, When the user
        opens the match wizard and creates the picking, Then an outgoing
        picking with the invoiced quantity exists for the partner."""
        invoice = self._invoice()
        action = invoice.action_match_or_create_picking()
        self.assertEqual(action["target"], "new")
        wizard = self.env[action["res_model"]].browse(action["res_id"])
        self.assertEqual(wizard.account_move_id, invoice)
        wizard.action_create_all()
        picking = wizard.new_stock_picking_ids
        self.assertEqual(len(picking), 1)
        self.assertEqual(picking.picking_type_id, self.warehouse.out_type_id)
        self.assertEqual(picking.partner_id, self.partner_a)
        self.assertEqual(picking.move_ids.product_id, self.product)
        self.assertEqual(picking.move_ids.product_uom_qty, 4.0)

    def test_vendor_bill_creates_incoming_picking(self):
        """Given a vendor bill, When the picking is created, Then it is an
        incoming picking (control: not the outgoing type used by sales)."""
        bill = self._invoice("in_invoice", qty=7.0)
        action = bill.action_match_or_create_picking()
        wizard = self.env[action["res_model"]].browse(action["res_id"])
        wizard.action_create_all()
        picking = wizard.new_stock_picking_ids
        self.assertEqual(picking.picking_type_code, "incoming")
        self.assertNotEqual(picking.picking_type_id, self.warehouse.out_type_id)
        self.assertEqual(picking.move_ids.product_uom_qty, 7.0)

    def test_invoice_without_product_lines_creates_no_picking(self):
        """Given an invoice with only a note, When create all runs, Then no
        picking is created."""
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    (0, 0, {"display_type": "line_note", "name": "Only a note"})
                ],
            }
        )
        action = invoice.action_match_or_create_picking()
        wizard = self.env[action["res_model"]].browse(action["res_id"])
        wizard.action_create_all()
        self.assertFalse(wizard.new_stock_picking_ids)

    def test_form_button_is_restricted_to_stock_users(self):
        """Given the invoice form view, Then the Match/Create Picking button
        exists and is limited to the stock user group."""
        view = self.env.ref(
            "account_move_picking_match_or_create.view_move_form_match_picking"
        )
        arch = self.env["account.move"].get_view(view.inherit_id.id, "form")["arch"]
        self.assertIn('name="action_match_or_create_picking"', arch)
        self.assertIn('groups="stock.group_stock_user"', view.arch_db)
