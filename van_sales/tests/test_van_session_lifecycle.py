from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon


@tagged("post_install", "-at_install")
class TestVanSessionLifecycle(TestPointOfSaleCommon):
    """BDD tests for the Van Sales session lifecycle.

    Scenarios covered:
        1. Path A — Link existing picking → session lines auto-created
        2. Path B — Manual lines → confirm → picking created & validated
        3. POS guard — cannot open POS without loaded van session
        4. POS sale + close → unload picking + session lines with sold qty
        5. Unload picking validation → in_move_line_ids populated
        6. action_post → closing account.move with correct debits/credits
        7. Constraint — one active session per driver
        8. Constraint — waive reason min 20 chars
        9. Price override — _get_price_unit uses pricelist price
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Grant van_sales access to the test user
        van_manager_group = cls.env.ref("van_sales.group_van_sales_manager")
        cls.env.user.groups_id = [(4, van_manager_group.id)]

        cls.company = cls.env.company
        warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )

        # Picking types for van load/unload
        cls.van_load_picking_type = cls.env["stock.picking.type"].create(
            {
                "name": "Van Load",
                "code": "internal",
                "sequence_code": "VLD",
                "warehouse_id": warehouse.id,
                "default_location_src_id": warehouse.lot_stock_id.id,
                "default_location_dest_id": cls.env["stock.location"]
                .create(
                    {
                        "name": "Van Stock",
                        "usage": "internal",
                        "location_id": warehouse.view_location_id.id,
                    }
                )
                .id,
            }
        )
        cls.van_location = cls.van_load_picking_type.default_location_dest_id

        cls.van_unload_picking_type = cls.env["stock.picking.type"].create(
            {
                "name": "Van Unload",
                "code": "internal",
                "sequence_code": "VUL",
                "warehouse_id": warehouse.id,
                "default_location_src_id": cls.van_location.id,
                "default_location_dest_id": warehouse.lot_stock_id.id,
            }
        )

        # Accounting setup
        cls.driver_account = cls.env["account.account"].create(
            {
                "code": "X1200",
                "name": "Van Driver Receivable",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        cls.transit_account = cls.env["account.account"].create(
            {
                "code": "X1300",
                "name": "Van Transit",
                "account_type": "asset_current",
            }
        )
        cls.van_cash_account = cls.env["account.account"].create(
            {
                "code": "X1400",
                "name": "Van Cash",
                "account_type": "asset_current",
            }
        )
        cls.van_journal = cls.env["account.journal"].create(
            {
                "name": "Van Journal",
                "code": "VAN",
                "type": "general",
                "company_id": cls.company.id,
            }
        )

        # Configure POS as van config
        cls.pos_config.write(
            {
                "is_van_config": True,
                "van_load_picking_type_id": cls.van_load_picking_type.id,
                "van_unload_picking_type_id": cls.van_unload_picking_type.id,
                "van_driver_account_id": cls.driver_account.id,
                "van_transit_account_id": cls.transit_account.id,
                "van_cash_account_id": cls.van_cash_account.id,
                "van_journal_id": cls.van_journal.id,
            }
        )

        # Driver
        cls.driver = cls.env["res.partner"].create(
            {
                "name": "João Motorista",
                "is_van_driver": True,
            }
        )

        # Products (storable, available in POS)
        cls.product_a = cls.env["product.product"].create(
            {
                "name": "Água Mineral",
                "is_storable": True,
                "available_in_pos": True,
                "list_price": 5.00,
                "standard_price": 2.00,
                "taxes_id": [(5, 0, 0)],
            }
        )
        cls.product_b = cls.env["product.product"].create(
            {
                "name": "Refrigerante",
                "is_storable": True,
                "available_in_pos": True,
                "list_price": 8.00,
                "standard_price": 3.50,
                "taxes_id": [(5, 0, 0)],
            }
        )

        # Put stock in warehouse
        cls.env["stock.quant"].with_context(inventory_mode=True).create(
            [
                {
                    "product_id": cls.product_a.id,
                    "inventory_quantity": 100,
                    "location_id": warehouse.lot_stock_id.id,
                },
                {
                    "product_id": cls.product_b.id,
                    "inventory_quantity": 100,
                    "location_id": warehouse.lot_stock_id.id,
                },
            ]
        ).action_apply_inventory()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_van_session(self, **kwargs):
        vals = {
            "driver_id": self.driver.id,
            "pos_config_id": self.pos_config.id,
        }
        vals.update(kwargs)
        return self.env["van.session"].create(vals)

    def _create_load_picking(self, products_qty):
        """Create and validate a load picking with given {product: qty} dict."""
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.van_load_picking_type.id,
                "location_id": self.van_load_picking_type.default_location_src_id.id,
                "location_dest_id": self.van_load_picking_type.default_location_dest_id.id,
            }
        )
        for product, qty in products_qty.items():
            self.env["stock.move"].create(
                {
                    "name": product.name,
                    "product_id": product.id,
                    "product_uom_qty": qty,
                    "product_uom": product.uom_id.id,
                    "picking_id": picking.id,
                    "location_id": picking.location_id.id,
                    "location_dest_id": picking.location_dest_id.id,
                }
            )
        picking.action_confirm()
        picking.action_assign()
        for ml in picking.move_line_ids:
            ml.quantity = ml.quantity_product_uom
        picking.move_ids.picked = True
        picking.button_validate()
        return picking

    def _open_pos_session(self, van_session):
        """Open POS session linked to a van session (auto-linked by open_ui)."""
        self.pos_config.open_ui()
        pos_session = self.pos_config.current_session_id
        # open_ui auto-links van_session ↔ pos_session and sets in_route
        self.assertEqual(pos_session.van_session_id, van_session)
        self.assertEqual(van_session.state, "in_route")
        return pos_session

    def _create_pos_order(self, pos_session, lines):
        """Create a POS order with given [(product, qty, price)] lines."""
        order = self.env["pos.order"].create(
            {
                "session_id": pos_session.id,
                "lines": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "qty": qty,
                            "price_unit": price,
                            "price_subtotal": qty * price,
                            "price_subtotal_incl": qty * price,
                            "tax_ids": [(5, 0, 0)],
                        },
                    )
                    for product, qty, price in lines
                ],
                "amount_total": sum(q * p for _, q, p in lines),
                "amount_tax": 0,
                "amount_paid": sum(q * p for _, q, p in lines),
                "amount_return": 0,
            }
        )
        cash_pm = pos_session.payment_method_ids.filtered(lambda pm: pm.is_cash_count)[
            :1
        ]
        self.env["pos.payment"].create(
            {
                "pos_order_id": order.id,
                "payment_method_id": cash_pm.id,
                "amount": order.amount_total,
            }
        )
        order.action_pos_order_paid()
        order._create_order_picking()
        return order

    def _close_pos_session(self, pos_session):
        """Close a POS session the standard way."""
        cash_pm = pos_session.payment_method_ids.filtered("is_cash_count")[:1]
        total_cash = sum(
            pos_session.order_ids.payment_ids.filtered(
                lambda p: p.payment_method_id == cash_pm
            ).mapped("amount")
        )
        pos_session.post_closing_cash_details(total_cash)
        pos_session.close_session_from_ui()

    # ==================================================================
    # SCENARIO 1: Path A — Link existing picking
    # ==================================================================

    def test_path_a_link_existing_picking_creates_session_lines(self):
        """GIVEN an existing validated load picking
        WHEN it is linked to a van session
        THEN session lines are auto-created with correct quantities and prices.
        """
        picking = self._create_load_picking(
            {
                self.product_a: 20,
                self.product_b: 10,
            }
        )

        session = self._create_van_session()
        session.load_picking_id = picking

        self.assertEqual(len(session.line_ids), 2)
        line_a = session.line_ids.filtered(lambda ln: ln.product_id == self.product_a)
        line_b = session.line_ids.filtered(lambda ln: ln.product_id == self.product_b)
        self.assertEqual(line_a.qty_out, 20)
        self.assertEqual(line_b.qty_out, 10)
        # Price should come from lst_price (no pricelist override)
        self.assertEqual(line_a.price_unit, 5.00)
        self.assertEqual(line_b.price_unit, 8.00)
        # Picking should be tagged
        self.assertEqual(picking.van_session_id, session)
        self.assertEqual(picking.van_type, "load")
        # Out move lines should be linked
        self.assertTrue(line_a.out_move_line_ids)
        self.assertTrue(line_b.out_move_line_ids)

    # ==================================================================
    # SCENARIO 2: Path B — Manual lines → confirm
    # ==================================================================

    def test_path_b_manual_lines_confirm_creates_picking(self):
        """GIVEN a van session in draft with manual lines
        WHEN action_confirm is called
        THEN a load picking is created, validated, and state becomes 'loaded'.
        """
        session = self._create_van_session()
        self.env["van.session.line"].create(
            [
                {
                    "session_id": session.id,
                    "product_id": self.product_a.id,
                    "qty_out": 15,
                    "price_unit": 5.00,
                },
                {
                    "session_id": session.id,
                    "product_id": self.product_b.id,
                    "qty_out": 8,
                    "price_unit": 8.00,
                },
            ]
        )

        session.action_confirm()

        self.assertEqual(session.state, "loaded")
        self.assertTrue(session.load_picking_id)
        self.assertEqual(session.load_picking_id.state, "done")
        self.assertEqual(session.load_picking_id.van_type, "load")
        self.assertEqual(session.load_picking_id.van_session_id, session)
        # Out move lines linked
        for line in session.line_ids:
            self.assertTrue(line.out_move_line_ids)

    def test_path_b_confirm_without_lines_raises(self):
        """GIVEN a van session in draft with no lines
        WHEN action_confirm is called
        THEN a UserError is raised.
        """
        session = self._create_van_session()
        with self.assertRaises(UserError):
            session.action_confirm()

    def test_path_b_confirm_non_draft_raises(self):
        """GIVEN a van session NOT in draft
        WHEN action_confirm is called
        THEN a UserError is raised.
        """
        session = self._create_van_session()
        self.env["van.session.line"].create(
            {
                "session_id": session.id,
                "product_id": self.product_a.id,
                "qty_out": 5,
                "price_unit": 5.00,
            }
        )
        session.action_confirm()
        self.assertEqual(session.state, "loaded")
        with self.assertRaises(UserError):
            session.action_confirm()

    # ==================================================================
    # SCENARIO 3: POS guard — cannot open without loaded session
    # ==================================================================

    def test_pos_guard_blocks_opening_without_loaded_session(self):
        """GIVEN a van POS config with NO loaded van session
        WHEN trying to open a new POS session
        THEN a UserError is raised.
        """
        with self.assertRaises(RedirectWarning):
            self.pos_config.open_ui()

    def test_pos_guard_allows_opening_with_loaded_session(self):
        """GIVEN a van POS config with a loaded van session
        WHEN opening a new POS session
        THEN it succeeds.
        """
        session = self._create_van_session()
        self.env["van.session.line"].create(
            {
                "session_id": session.id,
                "product_id": self.product_a.id,
                "qty_out": 10,
                "price_unit": 5.00,
            }
        )
        session.action_confirm()
        self.assertEqual(session.state, "loaded")

        self.pos_config.open_ui()
        self.assertTrue(self.pos_config.current_session_id)

    # ==================================================================
    # SCENARIO 4: POS sale + close → unload picking + sold qty
    # ==================================================================

    def test_pos_close_updates_sold_qty_and_sets_returned(self):
        """GIVEN a loaded van session with a POS session that has orders
        WHEN the POS session is closed
        THEN:
            - session lines qty_sold reflects POS sales
            - cash_diff is read from POS session
            - van session state becomes 'returned'
            - unload picking is NOT yet created (deferred to close wizard)
        """
        # Load
        session = self._create_van_session()
        self.env["van.session.line"].create(
            [
                {
                    "session_id": session.id,
                    "product_id": self.product_a.id,
                    "qty_out": 20,
                    "price_unit": 5.00,
                },
                {
                    "session_id": session.id,
                    "product_id": self.product_b.id,
                    "qty_out": 10,
                    "price_unit": 8.00,
                },
            ]
        )
        session.action_confirm()

        # Open POS and sell
        pos_session = self._open_pos_session(session)
        self._create_pos_order(
            pos_session,
            [
                (self.product_a, 5, 5.00),
                (self.product_b, 3, 8.00),
            ],
        )
        self._create_pos_order(
            pos_session,
            [
                (self.product_a, 3, 5.00),
            ],
        )

        # Close POS → triggers _on_pos_session_closed
        self._close_pos_session(pos_session)

        self.assertEqual(session.state, "returned")
        # Unload picking NOT yet created (deferred to action_post / wizard)
        self.assertFalse(session.unload_picking_id)

        # Session lines qty_sold updated
        line_a = session.line_ids.filtered(lambda ln: ln.product_id == self.product_a)
        line_b = session.line_ids.filtered(lambda ln: ln.product_id == self.product_b)
        self.assertEqual(line_a.qty_sold, 8)
        self.assertEqual(line_b.qty_sold, 3)

    def test_action_post_creates_unload_picking_with_correct_qty(self):
        """GIVEN a returned session with no unload picking
        WHEN action_post is called
        THEN unload picking is created with expected return quantities.
        """
        session = self._create_van_session()
        self.env["van.session.line"].create(
            [
                {
                    "session_id": session.id,
                    "product_id": self.product_a.id,
                    "qty_out": 20,
                    "price_unit": 5.00,
                },
                {
                    "session_id": session.id,
                    "product_id": self.product_b.id,
                    "qty_out": 10,
                    "price_unit": 8.00,
                },
            ]
        )
        session.action_confirm()
        pos_session = self._open_pos_session(session)
        self._create_pos_order(
            pos_session,
            [
                (self.product_a, 5, 5.00),
                (self.product_b, 3, 8.00),
            ],
        )
        self._create_pos_order(
            pos_session,
            [
                (self.product_a, 3, 5.00),
            ],
        )
        self._close_pos_session(pos_session)
        self.assertEqual(session.state, "returned")

        session.action_post()

        self.assertTrue(session.unload_picking_id)
        self.assertEqual(session.unload_picking_id.van_type, "unload")
        self.assertEqual(session.unload_picking_id.state, "done")

    # ==================================================================
    # SCENARIO 5: Unload picking validation → in_move_line_ids
    # ==================================================================

    def test_unload_validation_populates_in_move_lines(self):
        """GIVEN a returned van session with an unload picking
        WHEN the unload picking is validated with partial return
        THEN in_move_line_ids are populated on session lines
            and qty_returned / qty_diff are computed correctly.
        """
        # Setup: load → sell → close POS → get to returned state
        session = self._create_van_session()
        self.env["van.session.line"].create(
            [
                {
                    "session_id": session.id,
                    "product_id": self.product_a.id,
                    "qty_out": 20,
                    "price_unit": 5.00,
                },
            ]
        )
        session.action_confirm()
        pos_session = self._open_pos_session(session)
        self._create_pos_order(
            pos_session,
            [
                (self.product_a, 5, 5.00),
            ],
        )
        self._close_pos_session(pos_session)
        self.assertEqual(session.state, "returned")

        # Manually create unload picking (simulates action_post first step)
        session._create_unload_picking()

        # Validate unload picking (return 12 of 15 expected)
        unload = session.unload_picking_id
        unload.action_assign()
        for ml in unload.move_line_ids:
            ml.quantity = 12  # Return fewer than expected
        unload.move_ids.picked = True
        unload.button_validate()

        line_a = session.line_ids.filtered(lambda ln: ln.product_id == self.product_a)
        self.assertTrue(line_a.in_move_line_ids)
        self.assertEqual(line_a.qty_returned, 12)
        # qty_diff = 20 (out) - 5 (sold) - 12 (returned) = 3
        self.assertEqual(line_a.qty_diff, 3)
        # amount = 3 * 5.00 = 15.00
        self.assertEqual(line_a.amount, 15.00)

    # ==================================================================
    # SCENARIO 6: action_post → closing account.move
    # ==================================================================

    def test_action_post_creates_closing_journal_entry(self):
        """GIVEN a returned van session with qty differences
        WHEN action_post is called (with manually validated partial unload)
        THEN an account.move is created with correct debit/credit lines
            and the session state becomes 'closed'.
        """
        session = self._create_van_session()
        self.env["van.session.line"].create(
            [
                {
                    "session_id": session.id,
                    "product_id": self.product_a.id,
                    "qty_out": 20,
                    "price_unit": 5.00,
                },
            ]
        )
        session.action_confirm()
        pos_session = self._open_pos_session(session)
        self._create_pos_order(
            pos_session,
            [
                (self.product_a, 5, 5.00),
            ],
        )
        self._close_pos_session(pos_session)

        # Manually create and validate unload with partial return
        session._create_unload_picking()
        unload = session.unload_picking_id
        unload.action_assign()
        for ml in unload.move_line_ids:
            ml.quantity = 12
        unload.move_ids.picked = True
        unload.button_validate()

        # Now post (unload already done, action_post skips creation)
        session.action_post()

        self.assertEqual(session.state, "closed")
        self.assertTrue(session.move_id)
        self.assertEqual(session.move_id.state, "posted")

        # Check journal entry lines: diff = 3 * 5.00 = 15.00
        lines = session.move_id.line_ids
        driver_line = lines.filtered(
            lambda ln: ln.account_id == self.driver_account and ln.debit > 0
        )
        transit_line = lines.filtered(
            lambda ln: ln.account_id == self.transit_account and ln.credit > 0
        )
        self.assertTrue(driver_line)
        self.assertTrue(transit_line)
        self.assertEqual(driver_line.debit, 15.00)
        self.assertEqual(transit_line.credit, 15.00)

    def test_action_post_non_returned_raises(self):
        """GIVEN a van session NOT in 'returned' state
        WHEN action_post is called
        THEN a UserError is raised.
        """
        session = self._create_van_session()
        with self.assertRaises(UserError):
            session.action_post()

    def test_action_post_no_diff_closes_without_move(self):
        """GIVEN a returned session where everything sold matches out qty
        WHEN action_post is called
        THEN session closes with no account.move (no product or cash diff).
        """
        session = self._create_van_session()
        self.env["van.session.line"].create(
            {
                "session_id": session.id,
                "product_id": self.product_a.id,
                "qty_out": 10,
                "price_unit": 5.00,
            }
        )
        session.action_confirm()
        pos_session = self._open_pos_session(session)
        self._create_pos_order(
            pos_session,
            [
                (self.product_a, 10, 5.00),
            ],
        )
        self._close_pos_session(pos_session)

        self.assertEqual(session.state, "returned")
        # Ensure no cash diff for this test
        session.cash_diff = 0

        # Verify all qty_diff are zero (everything sold, nothing to return)
        line_a = session.line_ids.filtered(lambda ln: ln.product_id == self.product_a)
        self.assertEqual(line_a.qty_sold, 10)
        self.assertEqual(line_a.qty_diff, 0)

        session.action_post()
        self.assertEqual(session.state, "closed")
        self.assertFalse(session.move_id)

    def test_action_post_waived_lines_excluded(self):
        """GIVEN a returned session with waived difference lines
        WHEN action_post is called
        THEN waived lines are excluded from the closing entry.
        """
        session = self._create_van_session()
        self.env["van.session.line"].create(
            [
                {
                    "session_id": session.id,
                    "product_id": self.product_a.id,
                    "qty_out": 20,
                    "price_unit": 5.00,
                },
                {
                    "session_id": session.id,
                    "product_id": self.product_b.id,
                    "qty_out": 10,
                    "price_unit": 8.00,
                },
            ]
        )
        session.action_confirm()
        pos_session = self._open_pos_session(session)
        # Sell some of each
        self._create_pos_order(
            pos_session,
            [
                (self.product_a, 5, 5.00),
                (self.product_b, 3, 8.00),
            ],
        )
        self._close_pos_session(pos_session)

        # Manually create and validate unload with partial return
        session._create_unload_picking()
        unload = session.unload_picking_id
        unload.action_assign()
        move_a = unload.move_ids.filtered(lambda m: m.product_id == self.product_a)
        move_b = unload.move_ids.filtered(lambda m: m.product_id == self.product_b)
        # Return 13 of 15 expected for A (diff=2), 5 of 7 expected for B (diff=2)
        for ml in move_a.move_line_ids:
            ml.quantity = 13
        for ml in move_b.move_line_ids:
            ml.quantity = 5
        unload.move_ids.picked = True
        unload.button_validate()

        # Waive product_b difference
        line_b = session.line_ids.filtered(lambda ln: ln.product_id == self.product_b)
        line_b.write(
            {
                "waived": True,
                "waive_reason": (
                    "Produto danificado durante transporte" " - autorizado pelo gerente"
                ),
            }
        )

        session.action_post()

        # Only product_a diff in entry: 2 * 5.00 = 10.00 (product_b waived)
        driver_line = session.move_id.line_ids.filtered(
            lambda ln: ln.account_id == self.driver_account and ln.debit > 0
        )
        self.assertEqual(driver_line.debit, 10.00)

    # ==================================================================
    # SCENARIO 7: Constraint — one active session per driver
    # ==================================================================

    def test_unique_active_driver_constraint(self):
        """GIVEN a driver with an active (loaded) van session
        WHEN creating another session for the same driver and activating it
        THEN a ValidationError is raised.
        """
        # Create and load first session
        session1 = self._create_van_session()
        self.env["van.session.line"].create(
            {
                "session_id": session1.id,
                "product_id": self.product_a.id,
                "qty_out": 5,
                "price_unit": 5.00,
            }
        )
        session1.action_confirm()
        self.assertEqual(session1.state, "loaded")

        # Create second session for same driver — draft is OK
        session2 = self._create_van_session()
        self.env["van.session.line"].create(
            {
                "session_id": session2.id,
                "product_id": self.product_a.id,
                "qty_out": 5,
                "price_unit": 5.00,
            }
        )
        # But confirming should fail
        with self.assertRaises(ValidationError):
            session2.action_confirm()

    # ==================================================================
    # SCENARIO 8: Constraint — waive reason min 20 chars
    # ==================================================================

    def test_waive_reason_too_short_raises(self):
        """GIVEN a session line with waived=True
        WHEN waive_reason is shorter than 20 characters
        THEN a ValidationError is raised.
        """
        session = self._create_van_session()
        with self.assertRaises(ValidationError):
            self.env["van.session.line"].create(
                {
                    "session_id": session.id,
                    "product_id": self.product_a.id,
                    "qty_out": 5,
                    "price_unit": 5.00,
                    "waived": True,
                    "waive_reason": "Short reason",
                }
            )

    def test_waive_reason_valid_passes(self):
        """GIVEN a session line with waived=True
        WHEN waive_reason has 20+ characters
        THEN it succeeds.
        """
        session = self._create_van_session()
        line = self.env["van.session.line"].create(
            {
                "session_id": session.id,
                "product_id": self.product_a.id,
                "qty_out": 5,
                "price_unit": 5.00,
                "waived": True,
                "waive_reason": "Produto avariado no transporte - gerente autorizou",
            }
        )
        self.assertTrue(line.waived)

    # ==================================================================
    # SCENARIO 9: _get_price_unit override on van pickings
    # ==================================================================

    def test_price_unit_override_uses_pricelist_price(self):
        """GIVEN a van load picking linked to a van session
        WHEN _get_price_unit is called on its moves
        THEN the pricelist sale price is returned (not AVCO/standard).
        """
        session = self._create_van_session()
        self.env["van.session.line"].create(
            {
                "session_id": session.id,
                "product_id": self.product_a.id,
                "qty_out": 10,
                "price_unit": 5.00,
            }
        )
        session.action_confirm()

        # The load picking moves should use sale price
        move = session.load_picking_id.move_ids[0]
        prices = move._get_price_unit()
        # Should be pricelist price (lst_price = 5.00), not standard_price (2.00)
        price_value = list(prices.values())[0]
        self.assertEqual(price_value, 5.00)

    # ==================================================================
    # SCENARIO 10: Sequence generation
    # ==================================================================

    def test_session_name_sequence(self):
        """GIVEN a new van session
        WHEN it is created
        THEN name is generated from the VAN sequence.
        """
        session = self._create_van_session()
        self.assertTrue(session.name.startswith("VAN/"))
        self.assertNotEqual(session.name, "/")

    # ==================================================================
    # SCENARIO 11: Full lifecycle end-to-end
    # ==================================================================

    def test_full_lifecycle_load_sell_return_close(self):
        """End-to-end: draft → loaded → in_route → returned → closed."""
        # STEP 1: Create session with manual lines
        session = self._create_van_session()
        self.assertEqual(session.state, "draft")

        self.env["van.session.line"].create(
            [
                {
                    "session_id": session.id,
                    "product_id": self.product_a.id,
                    "qty_out": 20,
                    "price_unit": 5.00,
                },
                {
                    "session_id": session.id,
                    "product_id": self.product_b.id,
                    "qty_out": 10,
                    "price_unit": 8.00,
                },
            ]
        )

        # STEP 2: Confirm load → loaded
        session.action_confirm()
        self.assertEqual(session.state, "loaded")
        self.assertTrue(session.load_picking_id)

        # STEP 3: Open POS → in_route
        pos_session = self._open_pos_session(session)
        self.assertEqual(session.state, "in_route")

        # STEP 4: Sell some products
        self._create_pos_order(
            pos_session,
            [
                (self.product_a, 8, 5.00),
                (self.product_b, 6, 8.00),
            ],
        )

        # STEP 5: Close POS → returned (no unload picking yet)
        self._close_pos_session(pos_session)
        self.assertEqual(session.state, "returned")
        self.assertFalse(session.unload_picking_id)

        # STEP 6: Manually create unload and validate with partial return
        session._create_unload_picking()
        unload = session.unload_picking_id
        unload.action_assign()
        move_a = unload.move_ids.filtered(lambda m: m.product_id == self.product_a)
        move_b = unload.move_ids.filtered(lambda m: m.product_id == self.product_b)
        # Expected: A=12, B=4. Return A=10 (2 missing), B=4 (all)
        for ml in move_a.move_line_ids:
            ml.quantity = 10
        for ml in move_b.move_line_ids:
            ml.quantity = 4
        unload.move_ids.picked = True
        unload.button_validate()

        # Check computed fields
        line_a = session.line_ids.filtered(lambda ln: ln.product_id == self.product_a)
        line_b = session.line_ids.filtered(lambda ln: ln.product_id == self.product_b)
        self.assertEqual(line_a.qty_out, 20)
        self.assertEqual(line_a.qty_sold, 8)
        self.assertEqual(line_a.qty_returned, 10)
        self.assertEqual(line_a.qty_diff, 2)
        self.assertEqual(line_a.amount, 10.00)  # 2 * 5.00

        self.assertEqual(line_b.qty_diff, 0)
        self.assertEqual(line_b.amount, 0.00)

        # STEP 7: Post closing → closed (unload already validated)
        session.action_post()
        self.assertEqual(session.state, "closed")
        self.assertTrue(session.move_id)

        # Verify journal entry: only product_a diff = 10.00
        driver_debit = session.move_id.line_ids.filtered(
            lambda ln: ln.account_id == self.driver_account
        )
        self.assertEqual(sum(driver_debit.mapped("debit")), 10.00)

    # ==================================================================
    # SCENARIO 12: Residual stock — load from van warehouse
    # ==================================================================

    def test_load_from_stock_empty_warehouse(self):
        """GIVEN an empty van warehouse
        WHEN action_load_from_stock is called
        THEN no lines are created.
        """
        session = self._create_van_session()
        session.action_load_from_stock()
        self.assertFalse(session.line_ids)

    def test_load_from_stock_with_residual(self):
        """GIVEN stock in the van warehouse
        WHEN action_load_from_stock is called
        THEN lines are created with qty_initial and qty_out matching quant qty.
        """
        # Put stock in van location
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            [
                {
                    "product_id": self.product_a.id,
                    "inventory_quantity": 30,
                    "location_id": self.van_location.id,
                },
            ]
        ).action_apply_inventory()

        session = self._create_van_session()
        session.action_load_from_stock()

        self.assertEqual(len(session.line_ids), 1)
        line_a = session.line_ids.filtered(lambda ln: ln.product_id == self.product_a)
        self.assertEqual(line_a.qty_initial, 30)
        self.assertEqual(line_a.qty_out, 30)

    def test_confirm_with_residual_creates_partial_picking(self):
        """GIVEN a session with qty_initial=30 and qty_out=80
        WHEN action_confirm is called
        THEN picking is created only for qty_out - qty_initial = 50.
        """
        # Put stock in van location
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            [
                {
                    "product_id": self.product_a.id,
                    "inventory_quantity": 30,
                    "location_id": self.van_location.id,
                },
            ]
        ).action_apply_inventory()

        session = self._create_van_session()
        session.action_load_from_stock()
        # Increase qty_out to 80 (30 residual + 50 new)
        line_a = session.line_ids.filtered(lambda ln: ln.product_id == self.product_a)
        line_a.qty_out = 80

        session.action_confirm()

        self.assertEqual(session.state, "loaded")
        self.assertTrue(session.load_picking_id)
        # Picking should only have move for 50 (80 - 30)
        move = session.load_picking_id.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.product_uom_qty, 50)

    def test_confirm_all_residual_no_picking(self):
        """GIVEN a session where all qty_out equals qty_initial
        WHEN action_confirm is called
        THEN no picking is created (everything already in van).
        """
        # Put stock in van location
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            [
                {
                    "product_id": self.product_a.id,
                    "inventory_quantity": 30,
                    "location_id": self.van_location.id,
                },
            ]
        ).action_apply_inventory()

        session = self._create_van_session()
        session.action_load_from_stock()
        # qty_out = qty_initial = 30, no new load needed

        session.action_confirm()

        self.assertEqual(session.state, "loaded")
        self.assertFalse(session.load_picking_id)

    # ==================================================================
    # SCENARIO 13: qty_keep — keep stock in van
    # ==================================================================

    def test_qty_keep_reduces_unload_and_diff(self):
        """GIVEN a returned session with qty_keep set
        WHEN action_post is called (which creates unload picking)
        THEN unload qty excludes qty_keep and qty_diff excludes qty_keep.
        """
        session = self._create_van_session()
        self.env["van.session.line"].create(
            [
                {
                    "session_id": session.id,
                    "product_id": self.product_a.id,
                    "qty_out": 20,
                    "price_unit": 5.00,
                },
            ]
        )
        session.action_confirm()
        pos_session = self._open_pos_session(session)
        self._create_pos_order(
            pos_session,
            [
                (self.product_a, 5, 5.00),
            ],
        )
        self._close_pos_session(pos_session)
        self.assertEqual(session.state, "returned")

        # Set qty_keep in returned state (as the wizard would)
        line_a = session.line_ids.filtered(lambda ln: ln.product_id == self.product_a)
        line_a.qty_keep = 10

        # action_post creates unload (respecting qty_keep), validates, posts
        session.action_post()

        # Unload picking: expected = 20 - 5 - 10 = 5
        unload_move = session.unload_picking_id.move_ids.filtered(
            lambda m: m.product_id == self.product_a
        )
        self.assertEqual(unload_move.product_uom_qty, 5)

        # qty_diff should be 0: 20 - 5 - 5 (returned) - 10 (keep) = 0
        self.assertEqual(line_a.qty_diff, 0)
        self.assertEqual(line_a.amount, 0)

    def test_qty_keep_constraint_exceeds_remaining(self):
        """GIVEN a session line with qty_out=20 and qty_sold=5
        WHEN qty_keep is set to more than remaining (15)
        THEN a ValidationError is raised.
        """
        session = self._create_van_session()
        line = self.env["van.session.line"].create(
            {
                "session_id": session.id,
                "product_id": self.product_a.id,
                "qty_out": 20,
                "price_unit": 5.00,
            }
        )
        with self.assertRaises(ValidationError):
            line.qty_keep = 25  # more than qty_out - qty_sold (20 - 0 = 20)

    # ==================================================================
    # SCENARIO 14: Full residual lifecycle across two sessions
    # ==================================================================

    def test_residual_two_session_lifecycle(self):
        """End-to-end: Session 1 keeps stock → Session 2 starts with residual.

        Session 1: Load 20 → Sell 5 → Keep 10 → Return 5
        Session 2: Load from stock (10 in van) → Add 40 more → Confirm
                   → Picking only for 40
        """
        # SESSION 1
        session1 = self._create_van_session()
        self.env["van.session.line"].create(
            {
                "session_id": session1.id,
                "product_id": self.product_a.id,
                "qty_out": 20,
                "price_unit": 5.00,
            }
        )
        session1.action_confirm()

        pos_session1 = self._open_pos_session(session1)
        self._create_pos_order(
            pos_session1,
            [
                (self.product_a, 5, 5.00),
            ],
        )
        self._close_pos_session(pos_session1)
        self.assertEqual(session1.state, "returned")

        # Set qty_keep=10 in returned state (as wizard would)
        line1 = session1.line_ids.filtered(lambda ln: ln.product_id == self.product_a)
        line1.qty_keep = 10

        # action_post creates unload (5 units), validates, posts
        session1.action_post()
        self.assertEqual(session1.state, "closed")

        # Verify unload: expected = 20 - 5 - 10 = 5
        unload_move = session1.unload_picking_id.move_ids
        self.assertEqual(unload_move.product_uom_qty, 5)
        self.assertEqual(line1.qty_returned, 5)
        self.assertEqual(line1.qty_diff, 0)  # 20 - 5 - 5 - 10 = 0

        # SESSION 2 — van warehouse should have 10 units of product_a
        # (20 loaded - 5 sold via POS picking - 5 returned via unload = 10 remaining)
        session2 = self._create_van_session()
        session2.action_load_from_stock()

        line2 = session2.line_ids.filtered(lambda ln: ln.product_id == self.product_a)
        self.assertTrue(line2)
        self.assertEqual(line2.qty_initial, 10)
        self.assertEqual(line2.qty_out, 10)

        # Add more stock
        line2.qty_out = 50  # 10 residual + 40 new

        session2.action_confirm()
        self.assertEqual(session2.state, "loaded")
        self.assertTrue(session2.load_picking_id)

        # Picking should only move 40 units (50 - 10)
        load_move = session2.load_picking_id.move_ids.filtered(
            lambda m: m.product_id == self.product_a
        )
        self.assertEqual(load_move.product_uom_qty, 40)

    # ==================================================================
    # SCENARIO 15: Close wizard
    # ==================================================================

    def test_close_wizard_return_all(self):
        """GIVEN a returned session
        WHEN the close wizard is opened and 'Devolver Tudo' is clicked
        THEN all qty_keep are set to 0 and session closes normally.
        """
        session = self._create_van_session()
        self.env["van.session.line"].create(
            [
                {
                    "session_id": session.id,
                    "product_id": self.product_a.id,
                    "qty_out": 20,
                    "price_unit": 5.00,
                },
                {
                    "session_id": session.id,
                    "product_id": self.product_b.id,
                    "qty_out": 10,
                    "price_unit": 8.00,
                },
            ]
        )
        session.action_confirm()
        pos_session = self._open_pos_session(session)
        self._create_pos_order(
            pos_session,
            [
                (self.product_a, 5, 5.00),
                (self.product_b, 3, 8.00),
            ],
        )
        self._close_pos_session(pos_session)
        self.assertEqual(session.state, "returned")

        # Open wizard
        wizard = (
            self.env["van.session.close.wizard"]
            .with_context(active_id=session.id)
            .create({})
        )
        self.assertEqual(len(wizard.line_ids), 2)

        # Click "Devolver Tudo"
        wizard.action_return_all()
        self.assertTrue(all(ln.qty_keep == 0 for ln in wizard.line_ids))

        # Confirm
        wizard.action_confirm()
        self.assertEqual(session.state, "closed")
        # All qty_keep should be 0
        self.assertTrue(all(ln.qty_keep == 0 for ln in session.line_ids))

    def test_close_wizard_keep_all(self):
        """GIVEN a returned session
        WHEN the close wizard is opened and 'Manter Tudo' is clicked
        THEN qty_keep equals qty_remaining and unload has no moves.
        """
        session = self._create_van_session()
        self.env["van.session.line"].create(
            {
                "session_id": session.id,
                "product_id": self.product_a.id,
                "qty_out": 20,
                "price_unit": 5.00,
            }
        )
        session.action_confirm()
        pos_session = self._open_pos_session(session)
        self._create_pos_order(
            pos_session,
            [
                (self.product_a, 5, 5.00),
            ],
        )
        self._close_pos_session(pos_session)

        wizard = (
            self.env["van.session.close.wizard"]
            .with_context(active_id=session.id)
            .create({})
        )

        # Click "Manter Tudo"
        wizard.action_keep_all()
        self.assertEqual(wizard.line_ids[0].qty_keep, 15)  # 20 - 5

        wizard.action_confirm()
        self.assertEqual(session.state, "closed")
        line_a = session.line_ids.filtered(lambda ln: ln.product_id == self.product_a)
        self.assertEqual(line_a.qty_keep, 15)
        # Unload should have no moves (everything kept)
        self.assertFalse(session.unload_picking_id.move_ids)

    def test_close_wizard_partial_keep(self):
        """GIVEN a returned session
        WHEN wizard sets partial qty_keep
        THEN unload picking reflects partial return.
        """
        session = self._create_van_session()
        self.env["van.session.line"].create(
            {
                "session_id": session.id,
                "product_id": self.product_a.id,
                "qty_out": 20,
                "price_unit": 5.00,
            }
        )
        session.action_confirm()
        pos_session = self._open_pos_session(session)
        self._create_pos_order(
            pos_session,
            [
                (self.product_a, 5, 5.00),
            ],
        )
        self._close_pos_session(pos_session)

        wizard = (
            self.env["van.session.close.wizard"]
            .with_context(active_id=session.id)
            .create({})
        )
        # Keep 10 of 15 remaining
        wizard.line_ids[0].qty_keep = 10

        wizard.action_confirm()
        self.assertEqual(session.state, "closed")

        # Unload should have move for 5 (15 remaining - 10 keep)
        unload_move = session.unload_picking_id.move_ids
        self.assertEqual(len(unload_move), 1)
        self.assertEqual(unload_move.product_uom_qty, 5)
