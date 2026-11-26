# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestMrpProductionRequestSale(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.route_mto = cls.env.ref("stock.route_warehouse0_mto")
        cls.route_mto.active = True
        route_manufacture = cls.env.ref("mrp.route_warehouse0_manufacture")
        cls.customer = cls.env.ref("mrp_production_request_sale.res_partner_marcenaria")
        cls.table = cls.env.ref("mrp_production_request.product_mesa_jantar")
        cls.table.route_ids = route_manufacture | cls.route_mto
        cls.bom = cls.env.ref("mrp_production_request.mrp_bom_mesa_jantar")
        cls.bom_reinforced = cls.env.ref(
            "mrp_production_request_sale.mrp_bom_mesa_jantar_reforcada"
        )
        cls.top = cls.env.ref("mrp_production_request.product_component_tampo")
        cls.top.write(
            {
                "route_ids": [(6, 0, route_manufacture.ids)],
                "mrp_production_request": True,
            }
        )
        cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.top.product_tmpl_id.id,
                "product_qty": 1,
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.env.ref(
                                "mrp_production_request.product_component_pe"
                            ).id,
                            "product_qty": 2,
                        },
                    )
                ],
            }
        )

    def _sale_order(self, **line_vals):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.table.id,
                            "product_uom_qty": 2,
                            **line_vals,
                        },
                    )
                ],
            }
        )
        return order

    def test_request_from_sale_order(self):
        order = self._sale_order(
            explicit_bom_id=self.bom_reinforced.id,
            production_notes="Verniz fosco",
        )
        order.action_confirm()
        request = self.env["mrp.production.request"].search(
            [("sale_line_id", "in", order.order_line.ids)]
        )
        self.assertEqual(len(request), 1)
        self.assertEqual(request.bom_id, self.bom_reinforced)
        self.assertEqual(request.origin_sale_id, order)
        self.assertEqual(request.partner_id, self.customer)
        self.assertEqual(request.sale_person_id, order.user_id)
        self.assertEqual(request.notes_from_so, "Verniz fosco")
        request.button_approved()
        wizard = (
            self.env["mrp.production.request.create.mo"]
            .with_context(active_model="mrp.production.request", active_ids=request.ids)
            .create({"mo_qty": 2})
        )
        action = wizard.create_mo()
        production = self.env["mrp.production"].browse(action["res_id"])
        self.assertEqual(production.sale_line_id, order.order_line)

    def test_request_created_by_hand_takes_sale_line_data(self):
        order = self._sale_order(
            explicit_bom_id=self.bom_reinforced.id,
            production_notes="Verniz fosco",
        )
        request = self.env["mrp.production.request"].create(
            {
                "product_id": self.table.id,
                "product_uom_id": self.table.uom_id.id,
                "bom_id": self.bom.id,
                "product_qty": 2,
                "origin": order.name,
            }
        )
        self.assertEqual(request.origin_sale_id, order)
        self.assertEqual(request.bom_id, self.bom_reinforced)
        self.assertEqual(request.notes_from_so, "Verniz fosco")

    def test_manufactured_component_goes_to_sub_mo(self):
        production = self.env["mrp.production"].create(
            {
                "product_id": self.table.id,
                "bom_id": self.bom.id,
                "product_qty": 1,
            }
        )
        production.action_confirm()
        raw_move = production.move_raw_ids.filtered(
            lambda move: move.product_id == self.top
        )
        group = self.env["procurement.group"]
        group.run(
            [
                group.Procurement(
                    self.top,
                    1,
                    self.top.uom_id,
                    self.warehouse.lot_stock_id,
                    "Component",
                    production.name,
                    self.warehouse.company_id,
                    {
                        "warehouse_id": self.warehouse,
                        "move_dest_ids": raw_move,
                        "group_id": production.procurement_group_id,
                    },
                )
            ]
        )
        component_production = self.env["mrp.production"].search(
            [("product_id", "=", self.top.id)]
        )
        self.assertEqual(len(component_production), 1)
        self.assertTrue(component_production.is_sub_mo)
        self.assertFalse(
            self.env["mrp.production.request"].search(
                [("product_id", "=", self.top.id)]
            )
        )

    def test_line_created_after_confirmation(self):
        order = self._sale_order()
        order.action_confirm()
        self.assertFalse(order.order_line.created_after_sale_order_confirmed)
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.table.id,
                "product_uom_qty": 1,
            }
        )
        self.assertTrue(line.created_after_sale_order_confirmed)
        moves = self.env["stock.move"].search([("sale_line_id", "=", line.id)])
        self.assertTrue(moves)
        self.assertTrue(all(moves.mapped("created_after_sale_order_confirmed")))
