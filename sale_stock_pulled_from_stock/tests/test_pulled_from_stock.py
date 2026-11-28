from odoo.tests import TransactionCase


class TestPulledFromStock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.warehouse.mto_mts_management = True
        cls.mts_mto_route = cls.warehouse.mts_mto_rule_id.route_id
        cls.partner = cls.env["res.partner"].create({"name": "Cliente de teste"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Parafuso",
                "is_storable": True,
                "route_ids": [(6, 0, cls.mts_mto_route.ids)],
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.warehouse.lot_stock_id, 10
        )

    def _confirm_order(self, qty):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": qty})
                ],
            }
        )
        order.action_confirm()
        return order.picking_ids

    def test_mark_with_stock(self):
        picking = self._confirm_order(3)
        self.assertTrue(picking.move_ids.pulled_from_stock)
        self.assertTrue(picking.pulled_from_stock)
        self.assertTrue(picking.display_pulled_from_stock_button)

    def test_remove_mark_wizard(self):
        picking = self._confirm_order(3)
        action = picking.open_remove_mark()
        self.assertEqual(action["context"]["default_picking_id"], picking.id)
        self.env["stock.picking.remove_mark"].create(
            {"picking_id": picking.id}
        ).button_remove_mark()
        self.assertFalse(picking.display_pulled_from_stock_button)
        self.assertTrue(picking.pulled_from_stock)

    def test_wizards_open_for_regular_user(self):
        user = self.env["res.users"].create(
            {
                "name": "Wizard user",
                "login": "wizard_user_access",
                "groups_id": [(6, 0, [self.env.ref("stock.group_stock_user").id])],
            }
        )
        for model in ("stock.picking.remove_mark",):
            self.env[model].with_user(user).check_access("create")
