from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, TransactionCase


class TestBomLineSubstitute(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.warehouse.manufacture_steps = "pbm"
        Product = cls.env["product.product"]
        vals = {"type": "consu", "is_storable": True}
        cls.finished = Product.create({"name": "Finished", **vals})
        cls.component = Product.create({"name": "Component", **vals})
        cls.alternative = Product.create({"name": "Alternative", **vals})
        cls.other = Product.create({"name": "Other", **vals})
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.finished.product_tmpl_id.id,
                "product_qty": 1,
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.component.id,
                            "product_qty": 10,
                            "substitute_product_ids": [(6, 0, cls.alternative.ids)],
                        },
                    )
                ],
            }
        )
        stock = cls.warehouse.lot_stock_id
        cls.env["stock.quant"]._update_available_quantity(cls.component, stock, 4)
        cls.env["stock.quant"]._update_available_quantity(cls.alternative, stock, 20)

    def _create_production(self):
        form = Form(self.env["mrp.production"])
        form.product_id = self.finished
        form.bom_id = self.bom
        form.product_qty = 1
        production = form.save()
        production.action_confirm()
        picking = production.picking_ids
        move = picking.move_ids
        return production, picking, move

    def test_alternatives_reach_order_and_picking(self):
        production, picking, move = self._create_production()
        raw = production.move_raw_ids
        self.assertEqual(raw.substitute_product_ids, self.alternative)
        self.assertEqual(move.substitute_product_ids, self.alternative)

    def test_substitute_partial_quantity(self):
        production, picking, move = self._create_production()
        raw = production.move_raw_ids
        new_pick = move._substitute_component(self.alternative, 6)
        self.assertEqual(move.product_uom_qty, 4)
        self.assertTrue(move.has_been_replaced)
        self.assertEqual(new_pick.product_id, self.alternative)
        self.assertEqual(new_pick.product_uom_qty, 6)
        self.assertTrue(new_pick.is_substitute)
        self.assertEqual(new_pick.picking_id, picking)
        self.assertEqual(raw.product_uom_qty, 4)
        new_raw = production.move_raw_ids - raw
        self.assertEqual(new_raw.product_id, self.alternative)
        self.assertEqual(new_raw.product_uom_qty, 6)
        self.assertEqual(new_raw.move_orig_ids, new_pick)
        self.assertEqual(new_pick.move_dest_ids, new_raw)
        self.assertEqual(new_pick.state, "assigned")

    def test_substitute_keeps_lot_of_alternative(self):
        self.alternative.tracking = "lot"
        lot = self.env["stock.lot"].create(
            {"name": "LOT-ALT", "product_id": self.alternative.id}
        )
        self.env["stock.quant"]._update_available_quantity(
            self.alternative, self.warehouse.lot_stock_id, 5, lot_id=lot
        )
        production, picking, move = self._create_production()
        raw = production.move_raw_ids
        raw.to_replace = True
        new_pick = move._substitute_component(self.alternative, 3)
        self.assertEqual(new_pick.lot_id, lot)
        self.assertEqual((production.move_raw_ids - raw).lot_id, lot)
        self.assertFalse(raw.to_replace)

    def test_substitute_full_quantity_cancels_original(self):
        production, picking, move = self._create_production()
        raw = production.move_raw_ids
        move._substitute_component(self.alternative, 10)
        self.assertEqual(move.state, "cancel")
        self.assertEqual(raw.state, "cancel")
        active = production.move_raw_ids.filtered(lambda m: m.state != "cancel")
        self.assertEqual(active.product_id, self.alternative)
        self.assertEqual(active.product_uom_qty, 10)

    def test_substitute_not_allowed_product(self):
        production, picking, move = self._create_production()
        with self.assertRaises(UserError):
            move._substitute_component(self.other, 1)

    def test_alternative_equal_to_component(self):
        with self.assertRaises(ValidationError):
            self.bom.bom_line_ids.substitute_product_ids = self.component

    def test_wizards_open_for_regular_user(self):
        user = self.env["res.users"].create(
            {
                "name": "Wizard user",
                "login": "wizard_user_access",
                "groups_id": [(6, 0, [self.env.ref("mrp.group_mrp_user").id])],
            }
        )
        for model in ("stock.move.substitute",):
            self.env[model].with_user(user).check_access("create")

    def test_alternative_with_other_uom_category(self):
        weight = self.env.ref("uom.product_uom_kgm")
        heavy = self.env["product.product"].create(
            {
                "name": "Weighed alternative",
                "type": "consu",
                "is_storable": True,
                "uom_id": weight.id,
                "uom_po_id": weight.id,
            }
        )
        with self.assertRaises(ValidationError):
            self.bom.bom_line_ids.substitute_product_ids = heavy

    def test_substitute_move_has_no_alternatives(self):
        production, picking, move = self._create_production()
        new_pick = move._substitute_component(self.alternative, 6)
        self.assertTrue(new_pick.is_substitute)
        new_pick._compute_substitute_product_ids()
        self.assertFalse(new_pick.substitute_product_ids)

    def test_open_substitute_wizard_action(self):
        production, picking, move = self._create_production()
        action = move.action_open_substitute_wizard()
        self.assertEqual(action["res_model"], "stock.move.substitute")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"], {"default_move_id": move.id})

    def test_substitute_requires_move_supplying_an_order(self):
        production, picking, move = self._create_production()
        raw = production.move_raw_ids
        # o movimento do componente na ordem não abastece outra ordem
        with self.assertRaises(UserError):
            raw._substitute_component(self.alternative, 1)
        # o movimento da separação sem destino também não
        move.move_dest_ids = False
        with self.assertRaises(UserError):
            move._substitute_component(self.alternative, 1)

    def test_substitute_only_confirmed_moves(self):
        production, picking, move = self._create_production()
        move.state = "draft"
        with self.assertRaisesRegex(UserError, "Only confirmed moves"):
            move._substitute_component(self.alternative, 1)

    def test_substitute_quantity_out_of_range(self):
        production, picking, move = self._create_production()
        with self.assertRaisesRegex(UserError, "between zero"):
            move._substitute_component(self.alternative, 0)
        with self.assertRaisesRegex(UserError, "between zero"):
            move._substitute_component(self.alternative, 11)

    def test_substitute_more_than_order_needs(self):
        production, picking, move = self._create_production()
        production.move_raw_ids.with_context(no_procurement=True).product_uom_qty = 5
        with self.assertRaisesRegex(UserError, "needs less than that"):
            move._substitute_component(self.alternative, 6)

    def test_substitute_unreserves_when_demand_falls_below_reserved(self):
        production, picking, move = self._create_production()
        self.assertEqual(move.quantity, 4)
        move._substitute_component(self.alternative, 8)
        self.assertEqual(move.product_uom_qty, 2)
        self.assertEqual(move.quantity, 2)

    def test_substitute_wizard(self):
        production, picking, move = self._create_production()
        wizard_form = Form(
            self.env["stock.move.substitute"].with_context(default_move_id=move.id)
        )
        wizard_form.product_id = self.alternative
        wizard = wizard_form.save()
        # sugere o que falta reservar do componente (10 de demanda, 4 reservados)
        self.assertEqual(wizard.product_uom_qty, 6)
        self.assertEqual(wizard.available_qty, 20)
        self.assertEqual(wizard.substitute_product_ids, self.alternative)
        result = wizard.action_confirm()
        self.assertEqual(result["type"], "ir.actions.act_window_close")
        self.assertTrue(move.has_been_replaced)
        self.assertEqual(move.product_uom_qty, 4)

    def test_substitute_wizard_suggests_full_demand_when_reserved(self):
        self.env["stock.quant"]._update_available_quantity(
            self.component, self.warehouse.lot_stock_id, 10
        )
        production, picking, move = self._create_production()
        self.assertEqual(move.quantity, 10)
        wizard_form = Form(
            self.env["stock.move.substitute"].with_context(default_move_id=move.id)
        )
        wizard_form.product_id = self.alternative
        self.assertEqual(wizard_form.product_uom_qty, 10)
