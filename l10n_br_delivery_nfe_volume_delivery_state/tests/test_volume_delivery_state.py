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
