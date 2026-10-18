# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCommissionCron(TransactionCase):
    def test_cron_runs_without_commissions(self):
        self.env["sale.commission.cron"].cron_generate_next_month_commissions()

    def test_cron_record_points_to_helper(self):
        cron = self.env.ref(
            "sale_commission_cron.ir_cron_generate_next_month_commissions"
        )
        self.assertEqual(cron.model_id.model, "sale.commission.cron")
