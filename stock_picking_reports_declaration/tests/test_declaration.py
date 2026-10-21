# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeclaration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.product = cls.env["product.product"].create(
            {"name": "Declaration Product", "type": "consu"}
        )
        warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.picking = cls._picking(warehouse)

    @classmethod
    def _picking(cls, warehouse):
        picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.out_type_id.id,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": cls.env.ref("stock.stock_location_customers").id,
            }
        )
        cls.env["stock.move"].create(
            {
                "product_id": cls.product.id,
                "product_uom_qty": 1.0,
                "product_uom": cls.product.uom_id.id,
                "picking_id": picking.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
            }
        )
        return picking

    def _render(self, xmlid, picking=None):
        picking = picking or self.picking
        return (
            self.env["ir.actions.report"]
            ._render_qweb_html(xmlid, picking.ids)[0]
            .decode()
        )

    def test_layout_wizard_writes_company_declaration(self):
        """Given the Configure Document Layout wizard, When the declaration is
        typed, Then it is stored on the company."""
        wizard = self.env["base.document.layout"].create({})
        self.assertFalse(wizard.declaration_receipt)
        wizard.declaration_receipt = "<p>I received the goods.</p>"
        self.assertIn("I received the goods.", self.company.declaration_receipt)

    def test_wizard_shows_current_company_declaration(self):
        """Given a company with a declaration, When the wizard opens, Then it
        shows that text (related field)."""
        self.company.declaration_receipt = "<p>Existing declaration</p>"
        wizard = self.env["base.document.layout"].create({})
        self.assertIn("Existing declaration", wizard.declaration_receipt)

    def test_picking_operations_report_prints_declaration(self):
        """Given a declaration on the company, When printing Picking
        Operations, Then the text appears, as HTML and not escaped."""
        self.company.declaration_receipt = "<p>Received <b>in good order</b></p>"
        html = self._render("stock.action_report_picking")
        self.assertIn("Received <b>in good order</b>", html)

    def test_picking_report_without_declaration_has_no_text(self):
        """Given no declaration, Then the report does not carry the text."""
        self.company.declaration_receipt = False
        html = self._render("stock.action_report_picking")
        self.assertNotIn("in good order", html)

    def test_delivery_slip_prints_declaration(self):
        """Given a declaration, When printing the Delivery Slip, Then the text
        appears too."""
        self.company.declaration_receipt = "<p>Delivery declaration text</p>"
        html = self._render("stock.action_report_delivery")
        self.assertIn("Delivery declaration text", html)
        self.company.declaration_receipt = False
        self.assertNotIn(
            "Delivery declaration text", self._render("stock.action_report_delivery")
        )

    def test_each_picking_prints_its_own_company_declaration(self):
        """Given two companies with different declarations, When printing the
        picking of the second one, Then only its own text is printed."""
        company2 = self.env["res.company"].create({"name": "Declaration Co 2"})
        self.company.declaration_receipt = "<p>Declaration of company ONE</p>"
        company2.declaration_receipt = "<p>Declaration of company TWO</p>"
        warehouse2 = self.env["stock.warehouse"].search(
            [("company_id", "=", company2.id)], limit=1
        )
        picking2 = self._picking(warehouse2)
        self.assertEqual(picking2.company_id, company2)
        html = self._render("stock.action_report_picking", picking2)
        self.assertIn("company TWO", html)
        self.assertNotIn("company ONE", html)

    def test_declaration_is_sanitized(self):
        """Given an Html declaration with a script, When saved, Then the script
        is stripped so it cannot reach the printed report."""
        self.company.declaration_receipt = "<p>Safe</p><script>alert(1)</script>"
        self.assertIn("Safe", self.company.declaration_receipt)
        self.assertNotIn("script", self.company.declaration_receipt)
        self.assertNotIn("alert(1)", self._render("stock.action_report_picking"))

    def test_layout_view_has_declaration_field(self):
        """Given the layout wizard form, Then the field is displayed after the
        report footer."""
        arch = self.env["base.document.layout"].get_view(
            self.env.ref("web.view_base_document_layout").id
        )["arch"]
        self.assertIn("declaration_receipt", arch)
        self.assertLess(arch.index("report_footer"), arch.index("declaration_receipt"))

    def test_only_administrators_change_the_declaration(self):
        """Given a plain employee, When writing the declaration, Then access is
        denied; a settings manager can."""
        employee = self.env["res.users"].create(
            {
                "name": "Declaration employee",
                "login": "declaration_employee",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(AccessError):
            self.company.with_user(employee).declaration_receipt = "<p>Hack</p>"
        self.company.with_user(
            self.env.ref("base.user_admin")
        ).declaration_receipt = "<p>Official</p>"
        self.assertIn("Official", self.company.declaration_receipt)
