# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger
from odoo.tools.safe_eval import safe_eval

from ..models.crm_lead_stage_duration import display_duration


@tagged("post_install", "-at_install")
class TestCrmLeadStageDuration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Lead = cls.env["crm.lead"]
        cls.Line = cls.env["crm.lead.stage.duration"]
        cls.team = cls.env["crm.team"].create({"name": "Duration team"})
        cls.team2 = cls.env["crm.team"].create({"name": "Other team"})
        Stage = cls.env["crm.stage"]
        cls.stage_a = Stage.create({"name": "Stage A"})
        cls.stage_b = Stage.create({"name": "Stage B"})
        cls.stage_c = Stage.create({"name": "Stage C"})

    def _lead(self, stage=None, **vals):
        vals.setdefault("name", "Duration lead")
        vals.setdefault("type", "opportunity")
        vals.setdefault("team_id", self.team.id)
        vals["stage_id"] = (stage or self.stage_a).id
        return self.Lead.create(vals)

    def _lines(self, lead):
        return self.Line.search([("lead_id", "in", lead.ids)], order="id")

    # display_duration -----------------------------------------------------

    def test_display_duration_units_and_plurals(self):
        """Given 1 week, 2 days, 1 hour, then each unit is named and pluralized."""
        seconds = 604800 + 2 * 86400 + 3600
        self.assertEqual(display_duration(seconds, 3), "1 w, 2 days, 1 hour")

    def test_display_duration_granularity(self):
        """Given 3725s, granularity limits how many units are shown."""
        self.assertEqual(display_duration(3725, 4), "1 hour, 2 min, 5 sec")
        self.assertEqual(display_duration(3725, 2), "1 hour, 2 min")

    def test_display_duration_empty_for_zero_none_negative(self):
        """Given zero, None or negative seconds, the text is empty."""
        self.assertEqual(display_duration(0), "")
        self.assertEqual(display_duration(None), "")
        self.assertEqual(display_duration(-50), "")

    # stage history on lead lifecycle -----------------------------------------

    def test_create_opens_running_line_in_current_stage(self):
        """Given a new lead in stage A, one running line is opened for it."""
        lead = self._lead()
        lines = self._lines(lead)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.stage_id, self.stage_a)
        self.assertEqual(lines.team_id, self.team)
        self.assertEqual(lines.user_id, self.env.user)
        self.assertFalse(lines.end_date)
        self.assertTrue(lines.running)
        self.assertEqual(lead.stage_duration_ids, lines)

    def test_stage_change_closes_line_and_opens_next_without_gap(self):
        """Given a lead in A, when it moves to B, A closes exactly when B starts."""
        lead = self._lead()
        first = self._lines(lead)
        lead.write({"stage_id": self.stage_b.id})
        lines = self._lines(lead)
        self.assertEqual(len(lines), 2)
        second = lines - first
        self.assertTrue(first.end_date)
        self.assertFalse(first.running)
        self.assertEqual(first.end_date, second.start_date)
        self.assertEqual(second.stage_id, self.stage_b)
        self.assertTrue(second.running)

    def test_write_without_stage_change_keeps_history(self):
        """Given a lead, when other fields or the same stage are written, nothing changes."""
        lead = self._lead()
        before = self._lines(lead)
        lead.write({"name": "Renamed"})
        lead.write({"stage_id": self.stage_a.id})
        self.assertEqual(self._lines(lead), before)
        self.assertTrue(before.running)

    def test_batch_create_gives_each_lead_a_line(self):
        """Given several leads created at once, each gets its own running line."""
        leads = self.Lead.create(
            [
                {
                    "name": name,
                    "type": "opportunity",
                    "stage_id": stage.id,
                    "team_id": self.team.id,
                }
                for name, stage in (("L1", self.stage_a), ("L2", self.stage_b))
            ]
        )
        self.assertEqual(self._lines(leads[0]).stage_id, self.stage_a)
        self.assertEqual(self._lines(leads[1]).stage_id, self.stage_b)
        self.assertEqual(len(self._lines(leads)), 2)

    def test_batch_stage_change_updates_every_lead(self):
        """Given two leads in A, when both move to C at once, both histories advance."""
        leads = self._lead(name="L1") | self._lead(name="L2")
        leads.write({"stage_id": self.stage_c.id})
        for lead in leads:
            lines = self._lines(lead)
            self.assertEqual(lines.mapped("stage_id"), self.stage_a | self.stage_c)
            self.assertEqual(lines.mapped("running"), [False, True])

    def test_only_changed_leads_get_new_lines_in_mixed_batch(self):
        """Given leads in A and B, when set to B, only the A lead moves."""
        in_a = self._lead(self.stage_a, name="In A")
        in_b = self._lead(self.stage_b, name="In B")
        (in_a | in_b).write({"stage_id": self.stage_b.id})
        self.assertEqual(len(self._lines(in_a)), 2)
        self.assertEqual(len(self._lines(in_b)), 1)

    def test_deleting_lead_removes_its_history(self):
        """Given a lead with history, when it is deleted, its lines cascade."""
        lead = self._lead()
        lines = self._lines(lead)
        lead.unlink()
        self.assertFalse(lines.exists())

    def test_copy_starts_a_fresh_history(self):
        """Given a lead with two stages, its copy has only its own running line."""
        lead = self._lead()
        lead.write({"stage_id": self.stage_b.id})
        copy = lead.copy()
        lines = self._lines(copy)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.stage_id, copy.stage_id)
        self.assertTrue(lines.running)
        self.assertEqual(len(self._lines(lead)), 2)

    # line model ------------------------------------------------------------------

    def test_line_inherits_lead_team_when_not_given(self):
        """Given a manual line without team, the lead team is used."""
        lead = self._lead()
        line = self.Line.create({"lead_id": lead.id, "stage_id": self.stage_b.id})
        self.assertEqual(line.team_id, self.team)

    def test_line_keeps_explicit_team(self):
        """Given a manual line with a team, the lead team does not override it."""
        lead = self._lead()
        line = self.Line.create(
            {"lead_id": lead.id, "stage_id": self.stage_b.id, "team_id": self.team2.id}
        )
        self.assertEqual(line.team_id, self.team2)

    def test_closed_line_duration(self):
        """Given start 10 min ago and end 2 min ago, duration is 8 minutes."""
        lead = self._lead()
        now = fields.Datetime.now()
        line = self.Line.create(
            {
                "lead_id": lead.id,
                "stage_id": self.stage_b.id,
                "start_date": now - timedelta(minutes=10),
                "end_date": now - timedelta(minutes=2),
            }
        )
        self.assertEqual(line.duration_seconds, 480)
        self.assertEqual(line.duration_display, "8 min")
        self.assertFalse(line.running)

    def test_running_line_duration_grows_until_now(self):
        """Given an open line started 1h ago, the duration is at least one hour."""
        lead = self._lead()
        line = self.Line.create(
            {
                "lead_id": lead.id,
                "stage_id": self.stage_b.id,
                "start_date": fields.Datetime.now() - timedelta(hours=1),
            }
        )
        self.assertGreaterEqual(line.duration_seconds, 3600)
        self.assertTrue(line.duration_display.startswith("1 hour"))
        self.assertTrue(line.running)

    def test_closing_a_line_updates_running_flag(self):
        """Given a running line, when end_date is set, it stops running."""
        line = self._lines(self._lead())
        self.assertTrue(line.running)
        line.end_date = fields.Datetime.now()
        self.assertFalse(line.running)

    def test_zero_duration_has_empty_display(self):
        """Given start equal to end, the duration is zero and display empty."""
        lead = self._lead()
        now = fields.Datetime.now()
        line = self.Line.create(
            {
                "lead_id": lead.id,
                "stage_id": self.stage_b.id,
                "start_date": now,
                "end_date": now,
            }
        )
        self.assertEqual(line.duration_seconds, 0)
        self.assertEqual(line.duration_display, "")

    def test_end_before_start_is_rejected(self):
        """Given end earlier than start, the database constraint rejects it."""
        lead = self._lead()
        now = fields.Datetime.now()
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.cr.savepoint():
                self.Line.create(
                    {
                        "lead_id": lead.id,
                        "stage_id": self.stage_b.id,
                        "start_date": now,
                        "end_date": now - timedelta(seconds=1),
                    }
                )

    # lead totals ---------------------------------------------------------------

    def test_current_stage_total_sums_every_visit_to_the_stage(self):
        """Given a lead that visited A twice (100s and 300s), the A total is 400s."""
        lead = self._lead(self.stage_b)
        base = fields.Datetime.now() - timedelta(days=1)
        self._lines(lead).unlink()
        for stage, start, end in (
            (self.stage_a, 0, 100),
            (self.stage_b, 100, 200),
            (self.stage_a, 200, 500),
        ):
            self.Line.create(
                {
                    "lead_id": lead.id,
                    "stage_id": stage.id,
                    "start_date": base + timedelta(seconds=start),
                    "end_date": base + timedelta(seconds=end),
                }
            )
        lead.stage_id = self.stage_a
        # the move above opened a new running line, close it for a fixed total
        self._lines(lead).filtered("running").unlink()
        lead.invalidate_recordset()
        self.assertEqual(lead.current_stage_total_duration_seconds, 400)
        self.assertEqual(lead.current_stage_total_duration, "6 min, 40 sec")

    def test_current_stage_total_includes_running_line(self):
        """Given a running line started 1h ago in the current stage, total passes 1h."""
        lead = self._lead()
        self._lines(lead).write(
            {"start_date": fields.Datetime.now() - timedelta(hours=1)}
        )
        lead.invalidate_recordset()
        self.assertGreaterEqual(lead.current_stage_total_duration_seconds, 3600)
        self.assertTrue(lead.current_stage_total_duration.startswith("1 hour"))

    def test_current_stage_total_ignores_other_stages(self):
        """Given time spent only in A, when the lead is in B, B total is small."""
        lead = self._lead()
        self._lines(lead).write(
            {"start_date": fields.Datetime.now() - timedelta(hours=5)}
        )
        lead.write({"stage_id": self.stage_b.id})
        lead.invalidate_recordset()
        self.assertLess(lead.current_stage_total_duration_seconds, 60)

    # report --------------------------------------------------------------------

    def _report(self, team, stage):
        self.env.flush_all()
        return self.env["crm.lead.stage.duration.report"].search(
            [("team_id", "=", team.id), ("stage_id", "=", stage.id)]
        )

    def test_report_aggregates_closed_lines_per_team_and_stage(self):
        """Given 3 closed visits (100/300/200s) by 2 leads, the report aggregates them."""
        lead1 = self._lead(self.stage_c, name="R1")
        lead2 = self._lead(self.stage_c, name="R2")
        base = fields.Datetime.now() - timedelta(days=2)
        for lead, seconds in ((lead1, 100), (lead1, 300), (lead2, 200)):
            self.Line.create(
                {
                    "lead_id": lead.id,
                    "stage_id": self.stage_b.id,
                    "team_id": self.team.id,
                    "start_date": base,
                    "end_date": base + timedelta(seconds=seconds),
                }
            )
        row = self._report(self.team, self.stage_b)
        self.assertEqual(len(row), 1)
        self.assertEqual(row.line_count, 3)
        self.assertEqual(row.lead_count, 2)
        self.assertEqual(row.closed_line_count, 3)
        self.assertEqual(row.running_line_count, 0)
        self.assertEqual(row.total_duration_seconds, 600)
        self.assertEqual(row.avg_duration_seconds, 200)
        self.assertEqual(row.min_duration_seconds, 100)
        self.assertEqual(row.max_duration_seconds, 300)
        self.assertEqual(row.avg_duration_display, "3 min, 20 sec")

    def test_report_counts_running_lines_up_to_now(self):
        """Given a line open for two hours, the report counts it as running."""
        lead = self._lead(self.stage_c, name="Run")
        self.Line.create(
            {
                "lead_id": lead.id,
                "stage_id": self.stage_a.id,
                "team_id": self.team2.id,
                "start_date": fields.Datetime.now() - timedelta(hours=2),
            }
        )
        row = self._report(self.team2, self.stage_a)
        self.assertEqual(row.running_line_count, 1)
        self.assertEqual(row.closed_line_count, 0)
        # the view uses the database NOW(), a bit earlier than the python clock
        self.assertGreaterEqual(row.avg_duration_seconds, 3600)
        self.assertLess(row.avg_duration_seconds, 7300)
        self.assertIn("hour", row.avg_duration_display)

    def test_report_separates_teams(self):
        """Given the same stage in two teams, the report has one row per team."""
        lead = self._lead(self.stage_c, name="Teams")
        base = fields.Datetime.now() - timedelta(days=2)
        for team, seconds in ((self.team, 60), (self.team2, 120)):
            self.Line.create(
                {
                    "lead_id": lead.id,
                    "stage_id": self.stage_b.id,
                    "team_id": team.id,
                    "start_date": base,
                    "end_date": base + timedelta(seconds=seconds),
                }
            )
        self.assertEqual(self._report(self.team, self.stage_b).avg_duration_seconds, 60)
        self.assertEqual(
            self._report(self.team2, self.stage_b).avg_duration_seconds, 120
        )

    def test_report_row_without_average_has_empty_display(self):
        """Given a transition of zero length, the average display is empty."""
        lead = self._lead(self.stage_c, name="Zero")
        now = fields.Datetime.now() - timedelta(days=1)
        self.Line.create(
            {
                "lead_id": lead.id,
                "stage_id": self.stage_c.id,
                "team_id": self.team2.id,
                "start_date": now,
                "end_date": now,
            }
        )
        row = self._report(self.team2, self.stage_c)
        self.assertEqual(row.avg_duration_seconds, 0)
        self.assertEqual(row.avg_duration_display, "")

    # access rights --------------------------------------------------------------

    def _user(self, login, group_xmlid):
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "email": "%s@example.com" % login,
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(group_xmlid).id,
                        ],
                    )
                ],
            }
        )

    def test_salesman_moves_stage_and_reads_history_but_cannot_delete(self):
        """Given a salesman, moving a lead logs history; deleting a line is denied."""
        salesman = self._user("bant_dur_sales", "sales_team.group_sale_salesman")
        lead = self._lead(user_id=salesman.id)
        lead.with_user(salesman).write({"stage_id": self.stage_b.id})
        lines = self._lines(lead).with_user(salesman)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines.sorted("id")[1].user_id, salesman)
        with self.assertRaises(AccessError):
            lines.unlink()
        report = self.env["crm.lead.stage.duration.report"].with_user(salesman)
        self.assertTrue(report.search([]))
        with self.assertRaises(AccessError):
            report.search([])[:1].write({"line_count": 1})

    def test_salesman_cannot_forge_history(self):
        """Given a salesman, creating or editing a stage line directly is denied:
        the history is written only by the lead itself."""
        salesman = self._user("bant_dur_forger", "sales_team.group_sale_salesman")
        lead = self._lead(user_id=salesman.id)
        line = self._lines(lead).with_user(salesman)
        with self.assertRaises(AccessError):
            self.Line.with_user(salesman).create(
                {
                    "lead_id": lead.id,
                    "stage_id": self.stage_c.id,
                    "start_date": fields.Datetime.now() - timedelta(days=30),
                }
            )
        with self.assertRaises(AccessError):
            line.write({"start_date": fields.Datetime.now() - timedelta(days=30)})
        with self.assertRaises(AccessError):
            line.write({"user_id": self.env.ref("base.user_admin").id})

    def test_salesman_moves_lead_twice_and_history_is_recorded(self):
        """Given a salesman, moving a lead twice closes his own line and opens
        a new one, all under his name, though he cannot write lines himself."""
        salesman = self._user("bant_dur_mover", "sales_team.group_sale_salesman")
        lead = self._lead(user_id=salesman.id).with_user(salesman)
        lead.write({"stage_id": self.stage_b.id})
        lead.write({"stage_id": self.stage_c.id})
        lines = self._lines(lead)
        self.assertEqual(
            lines.mapped("stage_id"), self.stage_a | self.stage_b | self.stage_c
        )
        self.assertEqual(lines[1:].mapped("user_id"), salesman)
        self.assertTrue(lines[1].end_date)
        self.assertFalse(lines[2].end_date)

    def test_sales_manager_can_delete_history_lines(self):
        """Given a sales manager, deleting a stage line is allowed."""
        manager = self._user("bant_dur_mgr", "sales_team.group_sale_manager")
        lead = self._lead()
        line = self._lines(lead).with_user(manager)
        line.unlink()
        self.assertFalse(self._lines(lead))

    # views / actions ------------------------------------------------------------------

    def test_records_action_only_lists_opportunities(self):
        """Given the records action, plain leads are outside its domain."""
        action = self.env.ref("crm_lead_stage_duration.action_crm_lead_stage_duration")
        opp = self._lead(name="Opp")
        plain = self._lead(name="Plain", type="lead")
        found = self.Line.search(safe_eval(action.domain))
        self.assertTrue(self._lines(opp) <= found)
        self.assertFalse(self._lines(plain) & found)

    def test_menus_visibility(self):
        """Given the menus, records need the manager group while analysis is open."""
        records = self.env.ref(
            "crm_lead_stage_duration.menu_crm_lead_stage_duration_records"
        )
        report = self.env.ref(
            "crm_lead_stage_duration.menu_crm_lead_stage_duration_report"
        )
        self.assertIn(self.env.ref("sales_team.group_sale_manager"), records.group_ids)
        self.assertFalse(report.group_ids)

    def test_views_are_loadable(self):
        """Given the module views, the lead form shows the history and the report views load."""
        form = self.Lead.get_view(self.env.ref("crm.crm_lead_view_form").id)["arch"]
        self.assertIn("stage_duration_ids", form)
        self.assertIn("current_stage_total_duration", form)
        Report = self.env["crm.lead.stage.duration.report"]
        for mode in ("graph", "pivot", "kanban", "list"):
            arch = Report.get_view(view_type=mode)["arch"]
            self.assertTrue(arch)
        self.assertIn(
            "avg_duration_display", Report.get_view(view_type="kanban")["arch"]
        )
