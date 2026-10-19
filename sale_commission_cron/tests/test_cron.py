# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCommissionCron(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, no_reset_password=True)
        )
        cls.commission = cls.env["commission"].create(
            {
                "name": "10% on net amount",
                "commission_type": "fixed",
                "fix_qty": 10.0,
                "amount_base_type": "net_amount",
            }
        )
        cls.agent = cls.env["res.partner"].create(
            {
                "name": "Cron Agent",
                "agent": True,
                "agent_type": "agent",
                "commission_id": cls.commission.id,
                "settlement": "monthly",
            }
        )
        cls.customer = cls.env["res.partner"].create({"name": "Cron Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "Cron Product", "list_price": 100.0}
        )

    def _post_invoice(self, invoice_date=None):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_date": invoice_date
                or fields.Date.context_today(self.env.user),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "quantity": 1,
                            "price_unit": 100.0,
                            "agent_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "agent_id": self.agent.id,
                                        "commission_id": self.commission.id,
                                    },
                                )
                            ],
                        },
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _settlements(self):
        return self.env["commission.settlement"].search(
            [("agent_id", "=", self.agent.id)]
        )

    def test_cron_record_points_to_helper(self):
        """
        Given the module installed
        When looking at the shipped cron
        Then it is active, daily and calls the helper model method
        """
        cron = self.env.ref(
            "sale_commission_cron.ir_cron_generate_next_month_commissions"
        )
        self.assertEqual(cron.model_id.model, "sale.commission.cron")
        self.assertTrue(cron.active)
        self.assertEqual(cron.interval_type, "days")
        self.assertIn("cron_generate_next_month_commissions", cron.code)

    def test_cron_runs_without_open_commissions(self):
        """
        Given an agent without any invoiced commission
        When the cron runs
        Then it finishes and creates no settlement
        """
        self.env["sale.commission.cron"].cron_generate_next_month_commissions()
        self.assertFalse(self._settlements())

    def test_cron_settles_open_invoice_commissions(self):
        """
        Given a posted invoice with an agent commission line not yet settled
        When the cron runs (it settles up to next month)
        Then a settlement is created for the agent with the commission amount
        and the agent line is marked as settled
        """
        invoice = self._post_invoice()
        agent_line = invoice.invoice_line_ids.agent_ids
        self.assertEqual(len(agent_line), 1)
        self.assertFalse(agent_line.settled)
        self.assertFalse(self._settlements())
        self.env["sale.commission.cron"].cron_generate_next_month_commissions()
        settlement = self._settlements()
        self.assertEqual(len(settlement), 1)
        self.assertAlmostEqual(settlement.total, 10.0)
        self.assertTrue(agent_line.settled)

    def test_cron_is_idempotent(self):
        """
        Given a commission already settled by a previous cron run
        When the cron runs again
        Then no extra settlement or line is created
        """
        self._post_invoice()
        cron = self.env["sale.commission.cron"]
        cron.cron_generate_next_month_commissions()
        first = self._settlements()
        cron.cron_generate_next_month_commissions()
        self.assertEqual(self._settlements(), first)
        self.assertEqual(len(first.line_ids), 1)

    def test_cron_uses_next_month_as_cutoff(self):
        """
        Given the cron helper
        When it creates the standard settlement wizard
        Then the cutoff date is one month after today
        """
        captured = {}
        wizard_model = type(self.env["commission.make.settle"])
        original_create = wizard_model.create

        def spy_create(model, vals):
            captured.update(vals)
            return original_create(model, vals)

        expected = fields.Date.context_today(self.env.user) + relativedelta(months=1)
        wizard_model.create = spy_create
        try:
            self.env["sale.commission.cron"].cron_generate_next_month_commissions()
        finally:
            wizard_model.create = original_create
        self.assertEqual(captured["date_to"], expected)

    def test_cron_runs_as_superuser_for_unprivileged_caller(self):
        """
        Given an internal user without commission rights
        When the cron helper runs under that user
        Then the wizard still works because it is created with sudo
        """
        self._post_invoice()
        user = self.env["res.users"].create(
            {
                "name": "Plain User",
                "login": "plain_cron_user",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.env["sale.commission.cron"].with_user(
            user
        ).cron_generate_next_month_commissions()
        self.assertEqual(len(self._settlements()), 1)
