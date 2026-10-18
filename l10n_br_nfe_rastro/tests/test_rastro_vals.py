# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRastroVals(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.wizard = cls.env["stock.invoice.onshipping"]
        cls.product = cls.env["product.product"].create(
            {
                "name": "Tracked product",
                "type": "consu",
                "is_storable": True,
                "tracking": "lot",
            }
        )

    def _lot(self, **vals):
        return self.env["stock.lot"].create(
            dict(
                {
                    "name": "LOT-001",
                    "product_id": self.product.id,
                    "company_id": self.env.company.id,
                },
                **vals,
            )
        )

    def test_no_lot_returns_false(self):
        move_line = self.env["stock.move.line"].new({"product_id": self.product.id})
        self.assertFalse(self.wizard._get_move_line_rastro_vals(move_line))

    def test_lot_vals_with_expiration(self):
        lot = self._lot(expiration_date=datetime(2030, 5, 20, 10, 0))
        move_line = self.env["stock.move.line"].new(
            {"product_id": self.product.id, "lot_id": lot.id, "quantity": 7.0}
        )
        vals = self.wizard._get_move_line_rastro_vals(move_line)
        self.assertEqual(vals["nfe40_nLote"], "LOT-001")
        self.assertEqual(vals["nfe40_qLote"], 7.0)
        self.assertEqual(vals["nfe40_dVal"].isoformat(), "2030-05-20")
