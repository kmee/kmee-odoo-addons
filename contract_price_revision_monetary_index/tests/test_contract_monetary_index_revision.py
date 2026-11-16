# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.contract.tests.test_contract import TestContractBase


@tagged("post_install", "-at_install")
class TestContractMonetaryIndexRevision(TestContractBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.index = cls.env["monetary.index"].create(
            {"name": "IPCA de teste", "code": "IPCATEST"}
        )
        cls.contract.write(
            {
                "revision_index_id": cls.index.id,
                "revision_date_base": "2017-02-01",
            }
        )

    def _set_rates(self, date_from, months, value):
        for i in range(months):
            self.env["monetary.index.rate"].create(
                {
                    "index_id": self.index.id,
                    "date": date_from + relativedelta(months=i),
                    "value": value,
                }
            )

    def _wizard(self, contracts, date_start="2018-02-01"):
        return (
            self.env["contract.price.revision.wizard"]
            .with_context(active_ids=contracts.ids, active_model=contracts._name)
            .create({"date_start": date_start, "variation_type": "index"})
        )

    def _apply(self, contracts=None, date_start="2018-02-01"):
        contracts = contracts or self.contract
        wizard = self._wizard(contracts, date_start)
        wizard.with_context(
            active_ids=contracts.ids, active_model=contracts._name
        ).action_apply()

    def _new_line(self):
        return self.contract.contract_line_ids.filtered("predecessor_contract_line_id")

    def test_next_date_and_period(self):
        self.assertEqual(self.contract.revision_next_date, date(2018, 2, 1))
        date_from, date_to = self.contract._get_monetary_index_period(date(2018, 2, 1))
        self.assertEqual(date_from, date(2017, 2, 1))
        self.assertEqual(date_to, date(2018, 1, 31))

    def test_revision_compound(self):
        self._set_rates(date(2017, 2, 1), 12, 1.0)
        self._apply()
        new_line = self._new_line()
        self.assertEqual(len(new_line), 1)
        self.assertAlmostEqual(new_line.price_unit, 100 * 1.01**12, places=2)
        self.assertAlmostEqual(new_line.revision_percent, 12.6825, places=4)
        self.assertEqual(new_line.revision_index_id, self.index)
        self.assertEqual(new_line.revision_period_start, date(2017, 2, 1))
        self.assertEqual(new_line.revision_period_end, date(2018, 1, 31))
        self.assertEqual(new_line.date_start, date(2018, 2, 1))
        self.assertEqual(self.acct_line.date_end, date(2018, 1, 31))
        self.assertEqual(self.contract.revision_date_base, date(2018, 2, 1))
        self.assertEqual(self.contract.revision_next_date, date(2019, 2, 1))
        self.assertIn("IPCA de teste", self.contract.message_ids[0].body)

    def test_missing_month_blocks_the_revision(self):
        self._set_rates(date(2017, 2, 1), 11, 1.0)
        with self.assertRaises(UserError):
            self._apply()
        self.assertFalse(self._new_line())

    def test_negative_variation_not_reduced(self):
        self._set_rates(date(2017, 2, 1), 12, -1.0)
        self._apply()
        self.assertAlmostEqual(self._new_line().price_unit, 100.0, places=2)

    def test_negative_variation_applied(self):
        self.contract.revision_negative_policy = "apply"
        self._set_rates(date(2017, 2, 1), 12, -1.0)
        self._apply()
        self.assertAlmostEqual(self._new_line().price_unit, 100 * 0.99**12, places=2)

    def test_cap(self):
        self.contract.revision_cap = 5.0
        self._set_rates(date(2017, 2, 1), 12, 1.0)
        self._apply()
        self.assertAlmostEqual(self._new_line().price_unit, 105.0, places=2)

    def test_contract_without_index(self):
        self.contract.revision_index_id = False
        with self.assertRaises(UserError):
            self._apply()

    def test_percentage_revision_still_works(self):
        wizard = (
            self.env["contract.price.revision.wizard"]
            .with_context(active_ids=self.contract.ids)
            .create(
                {
                    "date_start": "2018-02-01",
                    "variation_type": "percentage",
                    "variation_percent": 10.0,
                }
            )
        )
        wizard.with_context(active_ids=self.contract.ids).action_apply()
        new_line = self._new_line()
        self.assertAlmostEqual(new_line.price_unit, 110.0, places=2)
        self.assertFalse(new_line.revision_index_id)

    def test_preview(self):
        self._set_rates(date(2017, 2, 1), 12, 1.0)
        wizard = self._wizard(self.contract)
        self.assertIn("12.6825", str(wizard.index_preview))
        self.assertIn(self.contract.display_name, str(wizard.index_preview))

    def _prepare_cron(self, days_ahead):
        next_date = fields.Date.context_today(self.contract) + relativedelta(
            days=days_ahead
        )
        self.contract.revision_date_base = next_date - relativedelta(months=12)
        date_from, __ = self.contract._get_monetary_index_period(next_date)
        self._set_rates(date_from, 12, 0.5)
        return next_date

    def test_cron_schedules_one_activity(self):
        next_date = self._prepare_cron(days_ahead=3)
        self.env["contract.contract"]._cron_monetary_index_revision()
        activity_type = self.env.ref(
            "contract_price_revision_monetary_index.mail_activity_contract_revision"
        )
        activities = self.contract.activity_ids.filtered(
            lambda a: a.activity_type_id == activity_type
        )
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities.date_deadline, next_date)
        self.env["contract.contract"]._cron_monetary_index_revision()
        self.assertEqual(len(self.contract.activity_ids), 1)
        self.assertFalse(self._new_line())

    def test_cron_activity_user(self):
        self._prepare_cron(days_ahead=3)
        self.contract.user_id = False
        self.env["contract.contract"]._cron_monetary_index_revision()
        self.assertEqual(self.contract.activity_ids.user_id, self.contract.create_uid)

    def test_cron_activity_responsible(self):
        self._prepare_cron(days_ahead=3)
        user = self.env["res.users"].create({"name": "Approver", "login": "approver"})
        self.contract.user_id = user
        self.env["contract.contract"]._cron_monetary_index_revision()
        self.assertEqual(self.contract.activity_ids.user_id, user)

    def test_cron_waits_for_the_index(self):
        self._prepare_cron(days_ahead=3)
        self.index.rate_ids[:1].unlink()
        self.env["contract.contract"]._cron_monetary_index_revision()
        self.assertFalse(self.contract.activity_ids)

    def test_cron_applies_in_auto_mode(self):
        self.contract.revision_mode = "auto"
        next_date = self._prepare_cron(days_ahead=0)
        self.env["contract.contract"]._cron_monetary_index_revision()
        new_line = self._new_line()
        self.assertEqual(len(new_line), 1)
        self.assertEqual(new_line.date_start, next_date)
        self.assertAlmostEqual(new_line.price_unit, 100 * 1.005**12, places=2)
