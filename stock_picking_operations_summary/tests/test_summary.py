# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install")
class TestPickingSummary(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.product = cls.env["product.product"].create(
            {"name": "Summary Product A", "type": "consu"}
        )
        cls.product_b = cls.env["product.product"].create(
            {"name": "Summary Product B", "type": "consu"}
        )
        cls.dozen = cls.env.ref("uom.product_uom_dozen")
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.customers = cls.env.ref("stock.stock_location_customers")
        cls.picking = cls._new_picking()

    @classmethod
    def _new_picking(cls):
        return cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.warehouse.out_type_id.id,
                "location_id": cls.warehouse.lot_stock_id.id,
                "location_dest_id": cls.customers.id,
            }
        )

    def _add_move(self, qty, product=None, uom=None, picking=None, dest=None):
        product = product or self.product
        picking = picking or self.picking
        return self.env["stock.move"].create(
            {
                "name": product.name,
                "product_id": product.id,
                "product_uom_qty": qty,
                "product_uom": (uom or product.uom_id).id,
                "picking_id": picking.id,
                "location_id": picking.location_id.id,
                "location_dest_id": (dest or picking.location_dest_id).id,
            }
        )

    def test_empty_picking_has_no_summary(self):
        """Given a picking without moves, Then there is no summary line and
        the summary is not offered."""
        self.assertFalse(self.picking.has_summary)
        self.assertFalse(self.picking.summary_line_ids)

    def test_single_move_has_no_summary_tab(self):
        """Given one move, Then the tab is not offered but the single line is
        still computed with the move quantities."""
        self._add_move(2.0)
        self.assertFalse(self.picking.has_summary)
        self.assertEqual(len(self.picking.summary_line_ids), 1)
        self.assertEqual(self.picking.summary_line_ids.product_uom_qty, 2.0)

    def test_same_product_and_uom_are_summed(self):
        """Given two moves of the same product and UoM, Then the summary has a
        single line with the demand summed and the tab is offered."""
        self._add_move(2.0)
        self._add_move(3.5)
        self.assertTrue(self.picking.has_summary)
        line = self.picking.summary_line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_id, self.product)
        self.assertEqual(line.product_uom, self.product.uom_id)
        self.assertAlmostEqual(line.product_uom_qty, 5.5)
        self.assertEqual(line.location_id, self.picking.location_id)
        self.assertEqual(line.location_dest_id, self.picking.location_dest_id)

    def test_different_products_stay_in_separate_lines(self):
        """Given moves of two products, Then each keeps its own line and no
        summary tab is needed."""
        self._add_move(2.0)
        self._add_move(3.0, product=self.product_b)
        self.assertFalse(self.picking.has_summary)
        lines = self.picking.summary_line_ids
        self.assertEqual(len(lines), 2)
        by_product = {ln.product_id: ln.product_uom_qty for ln in lines}
        self.assertEqual(by_product[self.product], 2.0)
        self.assertEqual(by_product[self.product_b], 3.0)

    def test_different_uom_are_never_added_together(self):
        """Given the same product in Units and in Dozens, Then quantities are
        not mixed (1 unit + 1 dozen is not 2) and the tab is not offered."""
        self._add_move(1.0)
        self._add_move(1.0, uom=self.dozen)
        self.assertFalse(self.picking.has_summary)
        lines = self.picking.summary_line_ids
        self.assertEqual(len(lines), 2)
        self.assertEqual(
            set(lines.mapped("product_uom")), {self.product.uom_id, self.dozen}
        )
        self.assertEqual(set(lines.mapped("product_uom_qty")), {1.0})

    def test_same_product_split_by_destination_keeps_lines(self):
        """Given the same product going to two destinations, Then lines are not
        merged across locations."""
        other = self.env["stock.location"].create(
            {"name": "Other dest", "usage": "internal"}
        )
        self._add_move(2.0)
        self._add_move(4.0, dest=other)
        lines = self.picking.summary_line_ids
        self.assertEqual(len(lines), 2)
        self.assertEqual(
            {ln.location_dest_id: ln.product_uom_qty for ln in lines},
            {self.customers: 2.0, other: 4.0},
        )

    def test_done_quantities_are_summed(self):
        """Given two moves with done quantities, Then the line sums the done
        quantity as well."""
        move1 = self._add_move(5.0)
        move2 = self._add_move(5.0)
        # distinct descriptions keep confirmation from merging the two moves
        move1.description_picking = "first"
        move2.description_picking = "second"
        self.picking.action_confirm()
        self.assertEqual(len(self.picking.move_ids), 2)
        move1.quantity_done = 2.0
        move2.quantity_done = 3.0
        line = self.picking.summary_line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_uom_qty, 10.0)
        self.assertEqual(line.quantity_done, 5.0)

    def test_summary_follows_changes_in_moves(self):
        """Given a picking with one move, When a second equal move is added,
        Then the summary is recomputed and the tab shows up; removing it
        undoes both."""
        self._add_move(1.0)
        self.assertFalse(self.picking.has_summary)
        extra = self._add_move(2.0)
        self.assertTrue(self.picking.has_summary)
        self.assertEqual(self.picking.summary_line_ids.product_uom_qty, 3.0)
        extra.unlink()
        self.assertFalse(self.picking.has_summary)
        self.assertEqual(self.picking.summary_line_ids.product_uom_qty, 1.0)

    def test_each_picking_has_its_own_summary(self):
        """Given two pickings read together, Then each gets the lines of its
        own moves."""
        other = self._new_picking()
        self._add_move(1.0)
        self._add_move(1.0, product=self.product_b, picking=other)
        self._add_move(4.0, product=self.product_b, picking=other)
        both = self.picking | other
        self.assertEqual(self.picking.summary_line_ids.product_id, self.product)
        self.assertEqual(other.summary_line_ids.product_uom_qty, 5.0)
        self.assertEqual(both.mapped("has_summary"), [False, True])

    def test_stock_user_reads_summary_but_employee_cannot_use_model(self):
        """Given a stock user, Then the summary is readable on the picking even
        though lines are created with sudo; a plain employee has no access to
        the summary model nor to the picking."""
        self._add_move(1.0)
        self._add_move(2.0)
        user = self.env["res.users"].create(
            {
                "name": "Stock user",
                "login": "summary_stock_user",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("stock.group_stock_user").id,
                        ],
                    )
                ],
            }
        )
        employee = self.env["res.users"].create(
            {
                "name": "Employee",
                "login": "summary_employee",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        picking = self.picking.with_user(user)
        self.assertEqual(picking.summary_line_ids.product_uom_qty, 3.0)
        with self.assertRaises(AccessError):
            self.env["stock.picking.summary.line"].with_user(employee).create(
                {
                    "product_id": self.product.id,
                    "product_uom": self.product.uom_id.id,
                }
            )

    def test_report_prints_grouped_quantity(self):
        """Given two moves of the same product, When printing the Picking
        Summary report, Then the product appears once with the summed
        quantity under the Products Summary heading."""
        self._add_move(2.0)
        self._add_move(3.0)
        html = (
            self.env["ir.actions.report"]
            ._render_qweb_html(
                "stock_picking_operations_summary.picking_summary", self.picking.ids
            )[0]
            .decode()
        )
        self.assertIn("Products Summary", html)
        self.assertEqual(html.count("Summary Product A"), 1)
        self.assertIn("5.00", html)

    def test_report_action_is_bound_to_pickings(self):
        """Given the module, Then the Picking Summary report is available from
        the stock.picking Print menu and names the file after the picking."""
        report = self.env.ref("stock_picking_operations_summary.report_picking_summary")
        self.assertEqual(report.model, "stock.picking")
        self.assertEqual(report.binding_type, "report")
        self.assertTrue(report.binding_model_id)
        self.picking.partner_id = self.env.ref("base.res_partner_1")
        self.assertIn(
            report,
            self.env["ir.actions.report"].search([("model", "=", "stock.picking")]),
        )
        title = safe_eval(report.print_report_name, {"object": self.picking})
        self.assertEqual(
            title,
            "Picking Summary - %s - %s"
            % (self.picking.partner_id.name, self.picking.name),
        )

    def test_form_tab_only_when_summary_exists(self):
        """Given the picking form, Then the Summary page is declared and its
        visibility is bound to has_summary."""
        arch = self.env["stock.picking"].get_view(view_type="form")["arch"]
        self.assertIn('name="operations_summary"', arch)
        self.assertIn("has_summary", arch)
