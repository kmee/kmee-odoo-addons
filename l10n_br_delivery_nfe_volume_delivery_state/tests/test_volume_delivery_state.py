# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests import TransactionCase


class TestVolumeDeliveryState(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.move = cls.env.ref(
            "l10n_br_delivery_nfe_lot_volume.move_remessa_prateleiras"
        )
        cls.volume_1 = cls.env.ref(
            "l10n_br_delivery_nfe_lot_volume.volume_remessa_prateleiras_1"
        )
        cls.volume_2 = cls.env.ref(
            "l10n_br_delivery_nfe_volume_delivery_state.volume_remessa_prateleiras_2"
        )

    def test_move_reflects_delivered_volumes(self):
        self.assertEqual(self.volume_2.delivery_state, "delivered")
        self.assertEqual(self.move.qty_marked_delivered, 3)
        self.assertEqual(self.move.delivery_state, "waiting_delivery")

    def test_change_delivery_state_sets_date(self):
        self.volume_1.button_change_delivery_state()
        self.assertEqual(self.volume_1.delivery_state, "delivered")
        self.assertEqual(
            self.volume_1.delivery_date, fields.Date.context_today(self.volume_1)
        )
        self.assertEqual(self.move.qty_marked_delivered, 8)
        self.assertEqual(self.move.delivery_state, "delivered")
        self.volume_1.button_change_delivery_state()
        self.assertEqual(self.volume_1.delivery_state, "waiting")
        self.assertFalse(self.volume_1.delivery_date)

    def test_volume_color_follows_delivery_state(self):
        self.assertEqual(self.volume_1.delivery_state, "waiting")
        self.assertEqual(self.volume_1.color, 3)
        self.assertEqual(self.volume_2.delivery_state, "delivered")
        self.assertEqual(self.volume_2.color, 10)
        self.volume_1.button_change_delivery_state()
        self.assertEqual(self.volume_1.color, 10)

    def _new_move(self, location_dest):
        return self.env["stock.move"].create(
            {
                "name": "Movimento sem reserva",
                "product_id": self.move.product_id.id,
                "product_uom": self.move.product_uom.id,
                "product_uom_qty": 4,
                "location_id": self.move.location_id.id,
                "location_dest_id": location_dest.id,
            }
        )

    def test_move_not_to_customer_does_not_apply(self):
        internal = self.env["stock.location"].search(
            [("usage", "=", "internal")], limit=1
        )
        move = self._new_move(internal)
        self.assertEqual(move.delivery_state, "does_not_apply")
        self.assertEqual(move.qty_marked_delivered, 0)

    def test_move_without_reservation_is_waiting(self):
        move = self._new_move(self.move.location_dest_id)
        self.assertFalse(move.quantity)
        self.assertEqual(move.delivery_state, "waiting")

    def test_done_move_partially_delivered(self):
        # concluído, só 3 de 8 marcados como entregues
        self.move.state = "done"
        self.assertEqual(self.move.qty_marked_delivered, 3)
        self.assertEqual(self.move.delivery_state, "partially_delivered")
        self.volume_1.button_change_delivery_state()
        self.assertEqual(self.move.delivery_state, "delivered")
