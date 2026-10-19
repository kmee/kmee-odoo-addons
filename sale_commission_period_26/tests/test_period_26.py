# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date
from unittest import mock

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.commission.wizards.commission_make_settle import CommissionMakeSettle


@tagged("post_install", "-at_install")
class TestCommissionPeriod26(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, no_reset_password=True)
        )
        cls.wizard = cls.env["commission.make.settle"]
        Partner = cls.env["res.partner"]
        cls.agent_26 = Partner.create(
            {"name": "Agent 26", "agent": True, "settlement": "vinte_seis"}
        )
        cls.agent_monthly = Partner.create(
            {"name": "Agent Monthly", "agent": True, "settlement": "monthly"}
        )

    def test_settlement_option_is_available_on_partner(self):
        """
        Given the agent settlement selection
        When listing its options
        Then the 26 to 25 option exists and falls back to default on uninstall
        """
        field = self.env["res.partner"]._fields["settlement"]
        self.assertIn("vinte_seis", dict(field.selection))
        self.assertEqual(field.ondelete, {"vinte_seis": "set default"})
        self.assertEqual(self.agent_26.settlement, "vinte_seis")

    def test_period_start_on_or_after_26_is_same_month(self):
        """
        Given an agent that settles from the 26th to the 25th
        When the cutoff date is on day 26 or later
        Then the period starts on the 26th of that same month
        """
        for day in (26, 27, 31):
            self.assertEqual(
                self.wizard._get_period_start(self.agent_26, date(2026, 3, day)),
                date(2026, 3, 26),
            )

    def test_period_start_before_26_is_previous_month(self):
        """
        Given an agent that settles from the 26th to the 25th
        When the cutoff date is before day 26
        Then the period starts on the 26th of the previous month
        """
        for day in (1, 15, 25):
            self.assertEqual(
                self.wizard._get_period_start(self.agent_26, date(2026, 3, day)),
                date(2026, 2, 26),
            )

    def test_period_start_crosses_year_boundary(self):
        """
        Given a cutoff date in January before day 26
        When the period start is computed
        Then it falls on December 26 of the previous year
        """
        self.assertEqual(
            self.wizard._get_period_start(self.agent_26, date(2026, 1, 10)),
            date(2025, 12, 26),
        )

    def test_next_period_is_26th_of_next_month(self):
        """
        Given a period starting on the 26th
        When the next period date is computed
        Then it is the 26th of the following month (so the period ends on 25th)
        """
        self.assertEqual(
            self.wizard._get_next_period_date(self.agent_26, date(2026, 2, 26)),
            date(2026, 3, 26),
        )
        self.assertEqual(
            self.wizard._get_next_period_date(self.agent_26, date(2026, 12, 26)),
            date(2027, 1, 26),
        )

    def test_other_settlements_keep_standard_behavior(self):
        """
        Given a monthly agent
        When the period boundaries are computed
        Then the standard commission behavior applies (calendar month)
        """
        self.assertEqual(
            self.wizard._get_period_start(self.agent_monthly, date(2026, 3, 15)),
            date(2026, 3, 1),
        )
        self.assertEqual(
            self.wizard._get_next_period_date(self.agent_monthly, date(2026, 3, 1)),
            date(2026, 4, 1),
        )

    def test_missing_date_falls_back_to_standard(self):
        """
        Given a 26 to 25 agent but no cutoff date
        When the period start is requested
        Then the 26 rule is not applied and the standard method answers
        """
        with mock.patch.object(
            CommissionMakeSettle,
            "_get_period_start",
            lambda self, agent, date_to: "standard",
        ):
            self.assertEqual(
                self.wizard._get_period_start(self.agent_26, False), "standard"
            )

    def test_legacy_single_argument_super_signature(self):
        """
        Given a commission version whose period methods only take the agent
        When the 26 to 25 wizard delegates to it for another settlement type
        Then the method is called with the agent only
        """
        base = CommissionMakeSettle
        with mock.patch.object(
            base, "_get_period_start", lambda self, agent: "legacy-start"
        ), mock.patch.object(
            base, "_get_next_period_date", lambda self, agent: "legacy-next"
        ):
            self.assertEqual(
                self.wizard._get_period_start(self.agent_monthly, date(2026, 3, 1)),
                "legacy-start",
            )
            self.assertEqual(
                self.wizard._get_next_period_date(self.agent_monthly, date(2026, 3, 1)),
                "legacy-next",
            )
