# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockLotOrigin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.warehouse.out_type_id.use_create_lots = True
        cls.supplier = cls.env["res.partner"].create({"name": "Fornecedor"})
        cls.customer = cls.env["res.partner"].create({"name": "Cliente"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Produto rastreado",
                "type": "consu",
                "is_storable": True,
                "tracking": "lot",
            }
        )

    def _receive(self, lot_name, qty=10):
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.supplier.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": qty,
                            "price_unit": 1.0,
                        },
                    )
                ],
            }
        )
        order.button_confirm()
        picking = order.picking_ids
        picking.move_line_ids.write({"lot_name": lot_name})
        picking.button_validate()
        return order, picking

    def test_purchase_receipt_sets_origin(self):
        order, picking = self._receive("LT-ORIGEM-1")
        lot = self.env["stock.lot"].search(
            [("name", "=", "LT-ORIGEM-1"), ("product_id", "=", self.product.id)]
        )
        self.assertEqual(lot.origin_picking_id, picking)
        self.assertEqual(lot.origin, order.name)
        self.assertEqual(lot.origin_purchase_id, order)
        self.assertFalse(lot.origin_sale_id)
        self.assertEqual(
            lot.origin_purchase_id, picking.move_line_ids.lot_origin_purchase_id
        )

    def test_later_delivery_keeps_origin(self):
        order, picking = self._receive("LT-ORIGEM-2")
        lot = picking.move_line_ids.lot_id
        sale = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 4})
                ],
            }
        )
        sale.action_confirm()
        sale.picking_ids.button_validate()
        self.assertEqual(sale.picking_ids.state, "done")
        self.assertEqual(lot.origin_purchase_id, order)
        self.assertFalse(lot.origin_sale_id)

    def test_lot_created_on_delivery_has_sale_origin(self):
        sale = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 3})
                ],
            }
        )
        sale.action_confirm()
        picking = sale.picking_ids
        picking.move_ids.write(
            {
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "quantity": 3,
                            "lot_name": "LT-ORIGEM-VENDA",
                            "location_id": picking.location_id.id,
                            "location_dest_id": picking.location_dest_id.id,
                            "picking_id": picking.id,
                        },
                    )
                ]
            }
        )
        picking.button_validate()
        lot = self.env["stock.lot"].search(
            [("name", "=", "LT-ORIGEM-VENDA"), ("product_id", "=", self.product.id)]
        )
        self.assertEqual(lot.origin_sale_id, sale)
        self.assertFalse(lot.origin_purchase_id)
        self.assertEqual(lot.origin_picking_id, picking)

    def test_move_without_picking_gives_no_origin(self):
        lot = self.env["stock.lot"].create(
            {"name": "LT-AJUSTE", "product_id": self.product.id}
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 5, lot_id=lot
        )
        self.assertFalse(lot.origin_picking_id)
