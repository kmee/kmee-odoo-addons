# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPickingSummary(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.product = cls.env["product.product"].create(
            {"name": "Summary Product", "type": "consu"}
        )
        warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.out_type_id.id,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": cls.env.ref("stock.stock_location_customers").id,
            }
        )

    def _add_move(self, qty):
        return self.env["stock.move"].create(
            {
                "name": self.product.name,
                "product_id": self.product.id,
                "product_uom_qty": qty,
                "product_uom": self.product.uom_id.id,
                "picking_id": self.picking.id,
                "location_id": self.picking.location_id.id,
                "location_dest_id": self.picking.location_dest_id.id,
            }
        )

    def test_single_move_has_no_summary(self):
        self._add_move(2.0)
        self.assertFalse(self.picking.has_summary)

    def test_grouped_moves_are_summed(self):
        self._add_move(2.0)
        self._add_move(3.0)
        self.assertTrue(self.picking.has_summary)
        lines = self.picking.summary_line_ids
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.product_id, self.product)
        self.assertEqual(lines.product_uom_qty, 5.0)
