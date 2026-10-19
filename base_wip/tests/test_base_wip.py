# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta
from types import SimpleNamespace

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from ..models.base_wip import display_time
from ..models.base_wip_abstract import BaseWipAbstract


@tagged("post_install", "-at_install")
class TestBaseWip(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.wip = cls.env["base.wip"]
        cls.partner = cls.env["res.partner"].create({"name": "WIP partner"})
        cls.model_partner = cls.env["ir.model"]._get("res.partner")

    def _make_wip(self, state, start_ago, stop_ago=None, res_id=None):
        """Create a wip entry started ``start_ago`` seconds ago."""
        now = fields.Datetime.now()
        vals = {
            "model_id": self.model_partner.id,
            "res_id": res_id or self.partner.id,
            "state": state,
            "date_hour_start": now - timedelta(seconds=start_ago),
        }
        if stop_ago is not None:
            vals["date_hour_stop"] = now - timedelta(seconds=stop_ago)
            vals["wip_state"] = "closed"
        return self.wip.create(vals)

    # display_time -------------------------------------------------------

    def test_display_time_formats_units(self):
        """Given 3661s, when formatted, then hours, min and sec are listed."""
        self.assertEqual(display_time(3661, 3), "1 hour, 1 min, 1 sec")

    def test_display_time_plural_and_weeks(self):
        """Given 9 days and 2 hours, then weeks and plural days appear."""
        seconds = 604800 + 2 * 86400 + 2 * 3600
        self.assertEqual(display_time(seconds, 3), "1 w, 2 days, 2 hours")

    def test_display_time_granularity_truncates(self):
        """Given granularity 1, only the largest unit is shown."""
        self.assertEqual(display_time(3661, 1), "1 hour")

    def test_display_time_zero_is_empty(self):
        """Given zero seconds, the text is empty."""
        self.assertEqual(display_time(0), "")

    # base.wip -----------------------------------------------------------

    def test_start_creates_running_entry(self):
        """Given a record, when started, then a running wip is created."""
        self.wip.start("res.partner", self.partner.id, state="open")
        entry = self.wip.search([("res_id", "=", self.partner.id)])
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry.model_id, self.model_partner)
        self.assertEqual(entry.state, "open")
        self.assertEqual(entry.wip_state, "running")
        self.assertEqual(entry.user_id, self.env.user)
        self.assertFalse(entry.date_hour_stop)

    def test_start_default_state_is_draft(self):
        """Given no state, when started, then the wip state is draft."""
        self.wip.start("res.partner", self.partner.id)
        entry = self.wip.search([("res_id", "=", self.partner.id)])
        self.assertEqual(entry.state, "draft")

    def test_start_terminal_states_create_nothing(self):
        """Given done/cancelled states, start does not open a wip."""
        before = self.wip.search_count([("res_id", "=", self.partner.id)])
        self.wip.start("res.partner", self.partner.id, state="done")
        self.wip.start("res.partner", self.partner.id, state="cancelled")
        after = self.wip.search_count([("res_id", "=", self.partner.id)])
        self.assertEqual(before, after)

    def test_stop_closes_running_entry(self):
        """Given a running wip, when stopped, then it is closed with times."""
        entry = self._make_wip("open", 100)
        entry.stop()
        self.assertEqual(entry.wip_state, "closed")
        self.assertTrue(entry.date_hour_stop)
        self.assertTrue(entry.date_stop)

    def test_stop_keeps_already_closed_entry(self):
        """Given a closed wip, when stopped again, then stop time is kept."""
        entry = self._make_wip("open", 500, stop_ago=300)
        stop_before = entry.date_hour_stop
        entry.stop()
        self.assertEqual(entry.date_hour_stop, stop_before)

    def test_lead_time_of_closed_entry_uses_stop(self):
        """Given start 500s ago and stop 300s ago, lead time is 200s."""
        entry = self._make_wip("open", 500, stop_ago=300)
        self.assertAlmostEqual(entry.lead_time_seconds, 200, delta=1)
        self.assertEqual(entry.lead_time, "3 min, 20 sec")

    def test_lead_time_of_running_entry_uses_now(self):
        """Given a running wip started 1h ago, lead time is about 1h."""
        entry = self._make_wip("open", 3600)
        self.assertGreaterEqual(entry.lead_time_seconds, 3599)
        self.assertLess(entry.lead_time_seconds, 3700)
        self.assertTrue(entry.lead_time.startswith("1 hour"))

    # base.wip.abstract compute -----------------------------------------

    def _metrics(self, wips):
        """Run the abstract compute on a stand-in carrying only ``wip_ids``.

        base.wip.abstract has no concrete model in this module, so the
        compute is executed unbound on a plain object (the method only
        iterates over ``self`` and reads ``wip_ids``).
        """
        record = SimpleNamespace(wip_ids=wips)
        BaseWipAbstract._compute_time([record])
        return record

    def test_abstract_metrics_split_by_state(self):
        """Given wips in draft/open/pending/done, metrics are split by state."""
        wips = (
            self._make_wip("draft", 1000, stop_ago=900)  # 100s reaction
            | self._make_wip("open", 900, stop_ago=600)  # 300s logged/cycle
            | self._make_wip("pending", 600, stop_ago=500)  # 100s cycle
            | self._make_wip("done", 500, stop_ago=100)  # excluded
        )
        record = self._metrics(wips)
        self.assertAlmostEqual(record.reaction_time_float, 100, delta=1)
        self.assertAlmostEqual(record.logged_time_float, 300, delta=1)
        self.assertAlmostEqual(record.cycle_time_float, 400, delta=1)
        self.assertAlmostEqual(record.lead_time_float, 500, delta=1)
        self.assertAlmostEqual(record.flow_efficience, 0.8, places=2)
        self.assertEqual(record.reaction_time, "1 min, 40 sec")
        self.assertEqual(record.logged_time, "5 min")

    def test_abstract_metrics_without_wip_are_zero(self):
        """Given no wip entries, efficiency is zero (no division by zero)."""
        record = self._metrics(self.wip)
        self.assertEqual(record.lead_time_float, 0)
        self.assertEqual(record.flow_efficience, 0)
        self.assertEqual(record.lead_time, "")

    # base.wip.report ----------------------------------------------------

    def test_report_shows_latest_wip_per_record(self):
        """Given two wips of a record, the report has one row, the latest."""
        self._make_wip("draft", 1000, stop_ago=900)
        last = self._make_wip("open", 900)
        self.env.flush_all()
        rows = self.env["base.wip.report"].search([("res_id", "=", self.partner.id)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.id, last.id)
        self.assertEqual(rows.state, "open")

    def test_report_computes_times_and_reference(self):
        """Given wips, the report row exposes aggregated times and reference."""
        self._make_wip("draft", 1000, stop_ago=900)
        self._make_wip("open", 900, stop_ago=600)
        self._make_wip("open", 600)
        self.env.flush_all()
        row = self.env["base.wip.report"].search([("res_id", "=", self.partner.id)])
        self.assertAlmostEqual(row.reaction_time_float, 100, delta=1)
        self.assertGreaterEqual(row.logged_time_float, 899)
        self.assertGreaterEqual(row.lead_time_float, row.cycle_time_float)
        self.assertGreater(row.flow_efficience, 0.8)
        self.assertEqual(row.reference_id, self.partner)
        self.assertEqual(row.reaction_time, "1 min, 40 sec")

    def test_report_without_open_time_has_zero_efficiency(self):
        """Given only a done wip, lead time is zero and efficiency zero."""
        self._make_wip("done", 500, stop_ago=100)
        self.env.flush_all()
        row = self.env["base.wip.report"].search([("res_id", "=", self.partner.id)])
        self.assertEqual(row.lead_time_float, 0)
        self.assertEqual(row.flow_efficience, 0)

    def test_report_open_form_points_to_record(self):
        """Given a report row, open_form returns the form of the record."""
        self._make_wip("open", 100)
        self.env.flush_all()
        row = self.env["base.wip.report"].search([("res_id", "=", self.partner.id)])
        action = row.open_form()
        self.assertEqual(action["res_model"], "res.partner")
        self.assertEqual(action["res_id"], self.partner.id)
        self.assertEqual(action["name"], self.partner.name)

    def test_report_filters_by_model(self):
        """Given wips of another model, the report keeps them separated."""
        model_users = self.env["ir.model"]._get("res.users")
        self.wip.create(
            {"model_id": model_users.id, "res_id": self.partner.id, "state": "open"}
        )
        self._make_wip("open", 100)
        self.env.flush_all()
        rows = self.env["base.wip.report"].search([("res_id", "=", self.partner.id)])
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            set(rows.mapped("model_id.model")), {"res.partner", "res.users"}
        )
