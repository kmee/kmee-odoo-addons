# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestWorkorderPartialProduction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id |= cls.env.ref("mrp.group_mrp_routings")
        vals = {"type": "consu", "is_storable": True}
        cls.product = cls.env["product.product"].create({"name": "Finished", **vals})
        cls.comp_a = cls.env["product.product"].create({"name": "Comp A", **vals})
        cls.comp_b = cls.env["product.product"].create({"name": "Comp B", **vals})
        cls.wc = cls.env["mrp.workcenter"].create({"name": "Center"})
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.product.product_tmpl_id.id,
                "product_qty": 1,
                "operation_ids": [
                    (0, 0, {"name": "Cut", "workcenter_id": cls.wc.id, "sequence": 1}),
                    (0, 0, {"name": "Pack", "workcenter_id": cls.wc.id, "sequence": 2}),
                ],
            }
        )
        cut, pack = cls.bom.operation_ids.sorted("sequence")
        cls.env["mrp.bom.line"].create(
            [
                {
                    "bom_id": cls.bom.id,
                    "product_id": cls.comp_a.id,
                    "product_qty": 2,
                    "operation_id": cut.id,
                },
                {
                    "bom_id": cls.bom.id,
                    "product_id": cls.comp_b.id,
                    "product_qty": 1,
                    "operation_id": pack.id,
                },
            ]
        )
        stock = cls.env.ref("stock.stock_location_stock")
        cls.env["stock.quant"]._update_available_quantity(cls.comp_a, stock, 100)
        cls.env["stock.quant"]._update_available_quantity(cls.comp_b, stock, 100)

    def _mo(self, qty=10):
        mo = self.env["mrp.production"].create(
            {"product_id": self.product.id, "product_qty": qty, "bom_id": self.bom.id}
        )
        mo.action_confirm()
        mo.action_assign()
        first, last = mo.workorder_ids.sorted("sequence")
        return mo, first, last

    def _record(self, workorder, qty):
        wizard = self.env["mrp.workorder.register.production"].create(
            {"workorder_id": workorder.id, "qty_producing": qty}
        )
        wizard.action_record_production()

    def test_record_creates_proportional_consumption(self):
        _mo, first, _last = self._mo()
        self.assertEqual(first.available_production_qty, 10)
        self._record(first, 4)
        self.assertEqual(first.qty_produced, 4)
        self.assertEqual(first.line_ids.product_id, self.comp_a)
        self.assertEqual(first.line_ids.qty_done, 8)

    def test_limit_by_previous_work_order(self):
        _mo, first, last = self._mo()
        self.assertEqual(last.available_production_qty, 0)
        self._record(first, 4)
        self.assertEqual(last.available_production_qty, 4)
        self.assertEqual(last.state, "ready")
        with self.assertRaises(UserError):
            self._record(last, 5)
        self._record(last, 4)
        self.assertEqual(last.available_production_qty, 0)

    def test_limit_by_reserved_components(self):
        mo = self.env["mrp.production"].create(
            {"product_id": self.product.id, "product_qty": 10, "bom_id": self.bom.id}
        )
        mo.action_confirm()
        move = mo.move_raw_ids.filtered(lambda m: m.product_id == self.comp_a)
        move.quantity = 6
        first = mo.workorder_ids.sorted("sequence")[0]
        self.assertEqual(first.available_production_qty, 3)

    def test_post_partial_to_production(self):
        mo, first, last = self._mo(10)
        self._record(first, 6)
        self._record(last, 4)
        last.launch_production()
        self.assertEqual(mo.state, "done")
        self.assertEqual(mo.qty_produced, 4)
        backorder = mo.procurement_group_id.mrp_production_ids - mo
        self.assertEqual(backorder.product_qty, 6)
        consumed = mo.move_raw_ids.filtered(lambda m: m.product_id == self.comp_a)
        self.assertEqual(sum(consumed.mapped("quantity")), 8)

    def test_only_last_work_order_posts(self):
        _mo, first, _last = self._mo()
        self._record(first, 4)
        with self.assertRaises(UserError):
            first.launch_production()

    def test_correct_quantity(self):
        _mo, first, last = self._mo()
        self._record(first, 6)
        self._record(last, 4)
        with self.assertRaises(UserError):
            first.set_qty_produced(3)
        with self.assertRaises(UserError):
            last.set_qty_produced(7)
        first.set_qty_produced(4)
        self.assertEqual(first.qty_produced, 4)
        self.assertEqual(
            first.line_ids.filtered(lambda ln: ln.product_id == self.comp_a).qty_done, 8
        )
        last.set_qty_produced(1)
        self.assertEqual(last.qty_produced, 1)
        self.assertEqual(
            last.line_ids.filtered(lambda ln: ln.product_id == self.comp_b).qty_done, 1
        )

    def test_open_wizard_actions(self):
        _mo, first, _last = self._mo()
        action = first.open_record_production()
        self.assertEqual(action["res_model"], "mrp.workorder.register.production")
        self.assertEqual(action["context"], {"default_workorder_id": first.id})
        action = first.open_set_qty_produced()
        self.assertEqual(action["res_model"], "mrp.workorder.set.qty.produced")
        self.assertEqual(action["context"], {"default_workorder_id": first.id})

    def test_register_wizard_proposes_available_quantity(self):
        _mo, first, _last = self._mo()
        wizard = self.env["mrp.workorder.register.production"].create(
            {"workorder_id": first.id}
        )
        self.assertEqual(wizard.qty_producing, 10)
        self.assertEqual(wizard.available_production_qty, 10)
        result = wizard.action_record_production()
        self.assertEqual(result["type"], "ir.actions.act_window_close")
        self.assertEqual(first.qty_produced, 10)

    def test_record_quantity_must_be_positive(self):
        _mo, first, _last = self._mo()
        with self.assertRaisesRegex(UserError, "greater than zero"):
            first.record_production(0)
        with self.assertRaisesRegex(UserError, "greater than zero"):
            first.record_production(-1)

    def test_record_twice_accumulates_consumption(self):
        _mo, first, _last = self._mo()
        self._record(first, 3)
        self._record(first, 2)
        self.assertEqual(first.qty_produced, 5)
        self.assertEqual(len(first.line_ids), 1)
        self.assertEqual(first.line_ids.qty_done, 10)

    def test_set_qty_wizard(self):
        _mo, first, _last = self._mo()
        self._record(first, 6)
        wizard = self.env["mrp.workorder.set.qty.produced"].create(
            {"workorder_id": first.id}
        )
        self.assertEqual(wizard.qty_produced, 6)
        wizard.qty_produced = 2
        result = wizard.action_set_qty_produced()
        self.assertEqual(result["type"], "ir.actions.act_window_close")
        self.assertEqual(first.qty_produced, 2)
        self.assertEqual(first.line_ids.qty_done, 4)

    def test_correct_quantity_of_finished_or_cancelled_order(self):
        _mo, first, _last = self._mo()
        self._record(first, 6)
        for state in ("done", "cancel"):
            first.state = state
            with self.assertRaisesRegex(UserError, "cannot be corrected"):
                first.set_qty_produced(2)

    def test_correct_quantity_cannot_be_negative(self):
        _mo, first, _last = self._mo()
        self._record(first, 6)
        with self.assertRaisesRegex(UserError, "cannot be negative"):
            first.set_qty_produced(-1)

    def test_correct_quantity_cannot_exceed_previous_work_order(self):
        _mo, first, last = self._mo()
        self._record(first, 6)
        self._record(last, 6)
        # a ordem anterior perde quantidade fora do fluxo de correção
        first.qty_produced = 3
        self.assertEqual(last.previous_wo_produced_qty, 3)
        with self.assertRaisesRegex(UserError, "previous work order"):
            last.set_qty_produced(5)

    def test_post_without_recorded_quantity(self):
        _mo, _first, last = self._mo()
        self.assertEqual(last.qty_to_launch, 0)
        with self.assertRaisesRegex(UserError, "no quantity to post"):
            last.launch_production()

    def _tracked_mo(self, qty=10):
        self.product.tracking = "lot"
        self.comp_a.tracking = "lot"
        stock = self.env.ref("stock.stock_location_stock")
        lot = self.env["stock.lot"].create(
            {"name": "LOTE-A1", "product_id": self.comp_a.id}
        )
        self.env["stock.quant"]._update_available_quantity(
            self.comp_a, stock, 100, lot_id=lot
        )
        return self._mo(qty)

    def test_post_with_tracked_finished_product_and_component(self):
        mo, first, last = self._tracked_mo(10)
        self._record(first, 6)
        self._record(last, 6)
        last.launch_production()
        self.assertEqual(mo.state, "done")
        self.assertEqual(mo.qty_produced, 6)
        self.assertTrue(mo.lot_producing_id)
        self.assertEqual(mo.lot_producing_id.product_id, self.product)
        consumed = mo.move_raw_ids.filtered(lambda m: m.product_id == self.comp_a)
        self.assertEqual(consumed.move_line_ids.lot_id.name, "LOTE-A1")
        self.assertEqual(sum(consumed.mapped("quantity")), 12)

    def test_post_uses_lot_chosen_on_the_order(self):
        mo, first, last = self._tracked_mo(10)
        lot = self.env["stock.lot"].create(
            {"name": "LOTE-FIN", "product_id": self.product.id}
        )
        mo.lot_producing_id = lot
        self._record(first, 10)
        self._record(last, 10)
        last.launch_production()
        self.assertEqual(mo.lot_producing_id, lot)
        self.assertEqual(mo.state, "done")

    def test_post_reserves_lot_of_tracked_component_released(self):
        mo, first, last = self._tracked_mo(10)
        self._record(first, 6)
        self._record(last, 6)
        mo.do_unreserve()
        self.assertFalse(mo.move_raw_ids.move_line_ids)
        last.launch_production()
        self.assertEqual(mo.state, "done")
        consumed = mo.move_raw_ids.filtered(lambda m: m.product_id == self.comp_a)
        self.assertEqual(consumed.move_line_ids.lot_id.name, "LOTE-A1")

    def test_post_after_components_returned_to_stock(self):
        warehouse = self.env.ref("stock.warehouse0")
        warehouse.manufacture_steps = "pbm"
        mo, first, last = self._tracked_mo(10)
        picking = mo.move_raw_ids.move_orig_ids.picking_id
        picking.action_assign()
        picking.move_ids.picked = True
        picking.button_validate()
        self._record(first, 6)
        self._record(last, 6)
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=picking.id, active_model="stock.picking")
            .create({})
        )
        for line in wizard.product_return_moves:
            line.quantity = line.move_id.product_uom_qty
        return_picking = wizard._create_return()
        return_picking.action_assign()
        return_picking.move_ids.picked = True
        return_picking.button_validate()
        with self.assertRaisesRegex(UserError, "no lot available"):
            last.launch_production()
