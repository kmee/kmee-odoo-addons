# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged

from ..models.base_wip import display_time


@tagged("post_install", "-at_install")
class TestBaseWip(TransactionCase):
    def test_display_time(self):
        self.assertEqual(display_time(3661, 3), "1 hour, 1 min, 1 sec")
        self.assertEqual(display_time(0), "")

    def test_start_and_stop(self):
        wip = self.env["base.wip"]
        wip.start("res.partner", 1, state="open")
        record = wip.search(
            [("model_id.model", "=", "res.partner"), ("res_id", "=", 1)]
        )
        self.assertEqual(len(record), 1)
        self.assertEqual(record.wip_state, "running")
        record.stop()
        self.assertEqual(record.wip_state, "closed")
        self.assertTrue(record.date_hour_stop)
        self.assertGreaterEqual(record.lead_time_seconds, 0)

    def test_start_done_creates_nothing(self):
        wip = self.env["base.wip"]
        count = wip.search_count([])
        wip.start("res.partner", 1, state="done")
        self.assertEqual(wip.search_count([]), count)
