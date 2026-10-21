# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestMatchPicking(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.partner = cls.partner_a
        cls.other_partner = cls.partner_b
        cls.prod_a = cls._create_product("Match Product A")
        cls.prod_b = cls._create_product("Match Product B")
        cls.prod_c = cls._create_product("Match Product C")
        cls.env["stock.quant"]._update_available_quantity(
            cls.prod_a, cls.stock_location, 100
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.prod_b, cls.stock_location, 100
        )

    @classmethod
    def _create_product(cls, name):
        return cls.env["product.product"].create(
            {"name": name, "detailed_type": "product", "list_price": 10.0}
        )

    @classmethod
    def _create_invoice(cls, move_type="out_invoice", lines=None, partner=None):
        lines = lines or [(cls.prod_a, 3.0), (cls.prod_b, 2.0)]
        return cls.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": (partner or cls.partner).id,
                "invoice_date": "2024-03-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "quantity": qty,
                            "price_unit": 10.0,
                        },
                    )
                    for product, qty in lines
                ],
            }
        )

    def _create_picking(self, picking_type, partner, products, state="assigned"):
        if picking_type.code == "outgoing":
            src = self.stock_location
            dest = partner.property_stock_customer
        else:
            src = partner.property_stock_supplier
            dest = self.stock_location
        picking = self.env["stock.picking"].create(
            {
                "partner_id": partner.id,
                "picking_type_id": picking_type.id,
                "location_id": src.id,
                "location_dest_id": dest.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom_qty": 1.0,
                            "product_uom": product.uom_id.id,
                            "location_id": src.id,
                            "location_dest_id": dest.id,
                        },
                    )
                    for product in products
                ],
            }
        )
        if state in ("assigned", "done"):
            picking.action_confirm()
            picking.action_assign()
            if state == "done":
                for move in picking.move_ids:
                    move.quantity_done = move.product_uom_qty
                picking._action_done()
        return picking

    def _wizard(self, invoice):
        action = invoice.action_match_or_create_picking()
        return self.env[action["res_model"]].browse(action["res_id"])

    def test_action_opens_wizard_for_the_invoice(self):
        """Given an invoice, When the match action is called, Then a wizard
        bound to that invoice opens as a modal with the candidates computed."""
        invoice = self._create_invoice()
        picking = self._create_picking(
            self.warehouse.out_type_id, self.partner, self.prod_a
        )
        action = invoice.action_match_or_create_picking()
        self.assertEqual(action["res_model"], "account.move.match.picking")
        self.assertEqual(action["target"], "new")
        wizard = self.env[action["res_model"]].browse(action["res_id"])
        self.assertEqual(wizard.account_move_id, invoice)
        self.assertEqual(wizard.state, "main")
        self.assertEqual(wizard.candidate_stock_picking_ids, picking)
        self.assertEqual(wizard.candidate_stock_picking_count, 1)

    def test_candidates_filter_partner_state_and_direction(self):
        """Given pickings of other partner, draft state and incoming type,
        When candidates are computed for a customer invoice, Then only the
        ready/done outgoing pickings of the invoice partner are listed."""
        good_ready = self._create_picking(
            self.warehouse.out_type_id, self.partner, self.prod_a
        )
        good_done = self._create_picking(
            self.warehouse.out_type_id, self.partner, self.prod_b, state="done"
        )
        self._create_picking(
            self.warehouse.out_type_id, self.other_partner, self.prod_a
        )
        self._create_picking(
            self.warehouse.out_type_id, self.partner, self.prod_a, state="draft"
        )
        self._create_picking(self.warehouse.in_type_id, self.partner, self.prod_a)
        self.assertEqual(good_done.state, "done")
        wizard = self._wizard(self._create_invoice())
        self.assertEqual(wizard.candidate_stock_picking_ids, good_ready | good_done)
        self.assertEqual(
            wizard.candidate_match_line_ids.picking_id, good_ready | good_done
        )

    def test_vendor_bill_candidates_are_incoming_pickings(self):
        """Given a vendor bill, When candidates are computed, Then incoming
        pickings of the vendor are listed and outgoing ones are not."""
        incoming = self._create_picking(
            self.warehouse.in_type_id, self.partner, self.prod_a
        )
        self._create_picking(self.warehouse.out_type_id, self.partner, self.prod_a)
        bill = self._create_invoice("in_invoice")
        wizard = self._wizard(bill)
        self.assertEqual(wizard.candidate_stock_picking_ids, incoming)

    def test_already_linked_picking_is_not_a_candidate(self):
        """Given a picking already linked to the invoice, When candidates are
        computed, Then it is excluded."""
        invoice = self._create_invoice()
        linked = self._create_picking(
            self.warehouse.out_type_id, self.partner, self.prod_a
        )
        free = self._create_picking(
            self.warehouse.out_type_id, self.partner, self.prod_b
        )
        invoice.invoice_line_ids[0].move_line_ids = [(6, 0, linked.move_ids.ids)]
        self.assertEqual(invoice.picking_ids, linked)
        wizard = self._wizard(invoice)
        self.assertEqual(wizard.candidate_stock_picking_ids, free)

    def test_match_status_counts_only_product_lines(self):
        """Given an invoice with a note line and two product lines, When no
        match was made, Then 2 lines are counted, 0 matched, all unmatched."""
        invoice = self._create_invoice()
        invoice.write(
            {
                "invoice_line_ids": [
                    (0, 0, {"display_type": "line_note", "name": "Just a note"})
                ]
            }
        )
        wizard = self._wizard(invoice)
        self.assertEqual(wizard.count_lines, 2)
        self.assertEqual(wizard.count_lines_matched, 0)
        self.assertEqual(wizard.matching_progress, 0)
        self.assertEqual(len(wizard.unmatched_invoice_line_ids), 2)
        self.assertFalse(wizard.can_action_exact_match)
        self.assertTrue(wizard.can_action_create_all)
        self.assertTrue(wizard.can_action_match_create)

    def test_match_status_without_product_lines(self):
        """Given an invoice with only a section line, Then nothing can be
        created or matched and progress is zero (no division by zero)."""
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    (0, 0, {"display_type": "line_section", "name": "Section"})
                ],
            }
        )
        wizard = self._wizard(invoice)
        self.assertEqual(wizard.count_lines, 0)
        self.assertEqual(wizard.matching_progress, 0)
        self.assertFalse(wizard.can_action_create_all)
        self.assertFalse(wizard.can_action_match_create)

    def test_exact_match_links_lines_by_product(self):
        """Given a candidate picking with product A only, When exact match
        runs, Then only the invoice line of A is matched (50% progress)."""
        invoice = self._create_invoice()
        picking = self._create_picking(
            self.warehouse.out_type_id, self.partner, self.prod_a
        )
        wizard = self._wizard(invoice)
        self.assertTrue(wizard.can_action_exact_match)
        action = wizard.action_exact_match()
        self.assertEqual(action["res_id"], wizard.id)
        line_a = invoice.invoice_line_ids.filtered(
            lambda l: l.product_id == self.prod_a
        )
        line_b = invoice.invoice_line_ids - line_a
        self.assertEqual(wizard.matching_invoice_line_ids, line_a)
        self.assertEqual(wizard.stock_picking_ids, picking)
        self.assertEqual(wizard.unmatched_invoice_line_ids, line_b)
        self.assertEqual(wizard.count_lines_matched, 1)
        self.assertEqual(wizard.matching_progress, 50)

    def test_exact_match_ignores_pickings_without_the_product(self):
        """Given a candidate picking with an unrelated product, When exact
        match runs, Then nothing is matched."""
        invoice = self._create_invoice()
        self._create_picking(self.warehouse.out_type_id, self.partner, self.prod_c)
        wizard = self._wizard(invoice)
        wizard.action_exact_match()
        self.assertFalse(wizard.matching_invoice_line_ids)
        self.assertFalse(wizard.stock_picking_ids)
        self.assertEqual(wizard.matching_progress, 0)

    def test_create_all_builds_outgoing_picking(self):
        """Given a customer invoice with no pickings, When create all runs,
        Then an outgoing picking with one move per line (same product, qty and
        uom) is created for the partner and progress becomes 100%."""
        invoice = self._create_invoice()
        wizard = self._wizard(invoice)
        wizard.action_create_all()
        picking = wizard.new_stock_picking_ids
        self.assertEqual(len(picking), 1)
        self.assertEqual(picking.picking_type_id, self.warehouse.out_type_id)
        self.assertEqual(picking.partner_id, self.partner)
        self.assertEqual(picking.origin, invoice.name)
        self.assertEqual(
            picking.location_id, self.warehouse.out_type_id.default_location_src_id
        )
        qty = {m.product_id: m.product_uom_qty for m in picking.move_ids}
        self.assertEqual(qty, {self.prod_a: 3.0, self.prod_b: 2.0})
        self.assertEqual(
            picking.move_ids.product_uom, invoice.invoice_line_ids.product_uom_id
        )
        self.assertEqual(wizard.matching_progress, 100)
        self.assertFalse(wizard.unmatched_invoice_line_ids)
        self.assertFalse(wizard.can_action_create_all)

    def test_create_all_for_vendor_bill_builds_incoming_picking(self):
        """Given a vendor bill, When create all runs, Then the picking uses
        the incoming operation type."""
        bill = self._create_invoice("in_invoice")
        wizard = self._wizard(bill)
        wizard.action_create_all()
        picking = wizard.new_stock_picking_ids
        self.assertEqual(picking.picking_type_id, self.warehouse.in_type_id)
        self.assertEqual(picking.picking_type_code, "incoming")

    def test_create_all_only_for_unmatched_lines(self):
        """Given line A already matched by an existing picking, When create
        all runs, Then the new picking only carries product B."""
        invoice = self._create_invoice()
        self._create_picking(self.warehouse.out_type_id, self.partner, self.prod_a)
        wizard = self._wizard(invoice)
        wizard.action_exact_match()
        wizard.action_create_all()
        self.assertEqual(wizard.new_stock_picking_ids.move_ids.product_id, self.prod_b)
        self.assertEqual(wizard.new_stock_picking_ids.move_ids.product_uom_qty, 2.0)
        self.assertEqual(wizard.matching_progress, 100)

    def test_create_all_without_picking_type_does_nothing(self):
        """Given a company without outgoing operation types, When create all
        runs, Then no picking is created and the wizard just reopens."""
        invoice = self._create_invoice()
        self.env["stock.picking.type"].search(
            [("company_id", "=", self.company.id), ("code", "=", "outgoing")]
        ).write({"active": False})
        wizard = self._wizard(invoice)
        action = wizard.action_create_all()
        self.assertEqual(action["res_id"], wizard.id)
        self.assertFalse(wizard.new_stock_picking_ids)
        self.assertEqual(wizard.count_lines_matched, 0)

    def test_create_all_skips_nothing_when_all_lines_have_products(self):
        """Given the created picking is confirmed, Then the demand matches
        the invoiced quantities (the picking is usable)."""
        invoice = self._create_invoice()
        wizard = self._wizard(invoice)
        wizard.action_create_all()
        picking = wizard.new_stock_picking_ids
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(sum(picking.move_ids.mapped("product_uom_qty")), 5.0)

    def test_user_without_invoicing_group_cannot_use_wizard(self):
        """Given a user outside the invoicing groups, When creating the
        wizard, Then access is denied; an invoicing + stock user can use it."""
        outsider = self.env["res.users"].create(
            {
                "name": "Outsider",
                "login": "match_outsider",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(AccessError):
            self.env["account.move.match.picking"].with_user(outsider).create(
                {"account_move_id": self._create_invoice().id}
            )
        biller = self.env["res.users"].create(
            {
                "name": "Biller",
                "login": "match_biller",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("account.group_account_invoice").id,
                            self.env.ref("stock.group_stock_user").id,
                        ],
                    )
                ],
            }
        )
        invoice = self._create_invoice()
        wizard = (
            self.env["account.move.match.picking"]
            .with_user(biller)
            .create({"account_move_id": invoice.id})
        )
        self.assertTrue(wizard.exists())
