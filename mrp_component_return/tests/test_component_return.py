from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase


class TestComponentReturn(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].create(
            {
                "name": "Return Test Warehouse",
                "code": "RTW",
                "manufacture_to_resupply": True,
                "manufacture_steps": "pbm",
                "component_return_enabled": True,
            }
        )
        product_vals = {"type": "consu", "is_storable": True}
        cls.finished = cls.env["product.product"].create(
            dict(product_vals, name="Finished")
        )
        cls.comp_a = cls.env["product.product"].create(dict(product_vals, name="A"))
        cls.comp_b = cls.env["product.product"].create(dict(product_vals, name="B"))
        bom_form = Form(cls.env["mrp.bom"])
        bom_form.product_tmpl_id = cls.finished.product_tmpl_id
        for comp, qty in ((cls.comp_a, 1), (cls.comp_b, 4)):
            with bom_form.bom_line_ids.new() as line:
                line.product_id = comp
                line.product_qty = qty
        cls.bom = bom_form.save()
        for comp in (cls.comp_a, cls.comp_b):
            cls.env["stock.quant"]._update_available_quantity(
                comp, cls.warehouse.lot_stock_id, 100
            )

    def _new_production(self, qty=2):
        production = self.env["mrp.production"].create(
            {
                "product_id": self.finished.id,
                "bom_id": self.bom.id,
                "product_qty": qty,
                "picking_type_id": self.warehouse.manu_type_id.id,
            }
        )
        production.action_confirm()
        picking = production._get_component_pickings()
        picking.action_assign()
        picking.move_ids.picked = True
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        return production, picking

    def _consume(self, production, product, qty):
        move = production.move_raw_ids.filtered(lambda m: m.product_id == product)
        move.move_line_ids.write({"quantity": qty, "picked": True})
        move.picked = True

    def _return_wizard(self, picking):
        return (
            self.env["stock.return.picking"]
            .with_context(active_id=picking.id, active_model="stock.picking")
            .create({})
        )

    def _validate(self, pickings):
        pickings.action_assign()
        pickings.move_ids.picked = True
        pickings.button_validate()

    def test_return_type_created_on_enable(self):
        return_type = self.warehouse.component_return_type_id
        self.assertTrue(return_type)
        self.assertEqual(return_type.default_location_src_id, self.warehouse.pbm_loc_id)
        self.assertEqual(
            return_type.default_location_dest_id, self.warehouse.lot_stock_id
        )
        self.assertEqual(self.warehouse.pbm_type_id.return_picking_type_id, return_type)

    def test_return_limited_to_unconsumed(self):
        production, picking = self._new_production()
        self._consume(production, self.comp_b, 6)
        wizard = self._return_wizard(picking)
        lines = {line.product_id: line for line in wizard.product_return_moves}
        self.assertEqual(lines[self.comp_a].quantity, 2)
        self.assertEqual(lines[self.comp_b].quantity, 2)
        lines[self.comp_b].quantity = 3
        with self.assertRaises(UserError):
            wizard._create_return()
        lines[self.comp_b].quantity = 2
        lines[self.comp_a].quantity = 0
        return_picking = wizard._create_return()
        self.assertEqual(return_picking.move_ids.product_id, self.comp_b)
        self.assertEqual(return_picking.move_ids.product_uom_qty, 2)

    def test_force_return_all(self):
        production, picking = self._new_production()
        self._consume(production, self.comp_b, 6)
        self.assertTrue(production.has_pending_component_return)
        action = production.button_force_return_all()
        self.assertTrue(production.has_forced_return)
        returns = self.env["stock.picking"].search(action["domain"])
        self.assertTrue(returns.is_final_mo_return)
        self.assertEqual(
            returns.picking_type_id, self.warehouse.component_return_type_id
        )
        quantities = {m.product_id: m.product_uom_qty for m in returns.move_ids}
        self.assertEqual(quantities, {self.comp_a: 2, self.comp_b: 2})
        self._validate(returns)
        self.assertEqual(returns.state, "done")
        self.assertFalse(production.has_pending_component_return)
        with self.assertRaises(UserError):
            production.button_force_return_all()

    def test_cancel_blocked_with_pending_reservation(self):
        production, picking = self._new_production()
        with self.assertRaises(UserError):
            production.action_cancel()
        production.button_force_return_all()
        with self.assertRaises(UserError):
            production.action_cancel()  # open return
        self._validate(production._get_component_return_pickings())
        production.action_cancel()
        self.assertEqual(production.state, "cancel")

    def test_done_blocked_with_pending_reservation(self):
        production, picking = self._new_production(qty=1)
        production.qty_producing = 1
        self._consume(production, self.comp_a, 1)
        with self.assertRaisesRegex(UserError, "Return All"):
            production.button_mark_done()
        production.button_force_return_all()
        self._validate(production._get_component_return_pickings())
        self.assertFalse(production.has_pending_component_return)

    def test_pending_reservations_list(self):
        production, picking = self._new_production()
        domain = [("has_pending_component_return", "=", True)]
        self.assertIn(production, self.env["mrp.production"].search(domain))
        production.button_force_return_all()
        self._validate(production._get_component_return_pickings())
        self.assertNotIn(production, self.env["mrp.production"].search(domain))
        production2, picking2 = self._new_production()
        action = production2.action_resolve_component_return()
        self.assertEqual(action["context"]["active_id"], picking2.id)

    def test_produce_all_without_marking_consumption(self):
        production, picking = self._new_production(qty=2)
        production.button_mark_done()
        self.assertEqual(production.state, "done")
        self.assertFalse(production.has_pending_component_return)

    def test_partial_production_with_backorder(self):
        production, picking = self._new_production(qty=2)
        production.qty_producing = 1
        production._set_qty_producing(False)
        production.with_context(
            skip_backorder=True,
            skip_consumption=True,
            skip_immediate=True,
            mo_ids_to_backorder=production.ids,
        ).button_mark_done()
        self.assertEqual(production.state, "done")
        self.assertFalse(production.has_pending_component_return)
        backorder = production.procurement_group_id.mrp_production_ids - production
        self.assertTrue(backorder.has_pending_component_return)
        with self.assertRaises(UserError):
            backorder.action_cancel()
        backorder.button_mark_done()
        self.assertEqual(backorder.state, "done")
