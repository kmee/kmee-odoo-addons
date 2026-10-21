# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from lxml import etree

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from ..models.helpdesk_ticket_stage_duration_report import (
    display_duration as report_display_duration,
)
from ..models.helpdesk_ticket_track import display_duration


@tagged("post_install", "-at_install")
class TestStageDuration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        Stage = cls.env["helpdesk.ticket.stage"]
        cls.stage_new = Stage.create({"name": "LC New"})
        cls.stage_wip = Stage.create({"name": "LC In progress"})
        cls.stage_done = Stage.create({"name": "LC Done"})
        cls.team = cls.env["helpdesk.ticket.team"].create({"name": "LC Team"})
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.Duration = cls.env["helpdesk.ticket.stage.duration"]
        cls.ticket = cls._ticket(cls)

    def _ticket(self, **kw):
        vals = {
            "name": "Ticket",
            "description": "d",
            "team_id": self.team.id,
            "stage_id": self.stage_new.id,
        }
        vals.update(kw)
        return self.Ticket.create(vals)

    def test_display_duration_formats(self):
        """Given durations in seconds
        When formatted
        Then units are singular/plural and limited by granularity."""
        self.assertEqual(display_duration(90061, 3), "1 day, 1 hour, 1 min")
        self.assertEqual(display_duration(0), "")
        self.assertEqual(display_duration(2 * 604800 + 2 * 86400, 4), "2 w, 2 days")
        self.assertEqual(display_duration(59, 2), "59 sec")
        self.assertEqual(display_duration(3661), "1 hour, 1 min")
        self.assertEqual(report_display_duration(3661, 3), "1 hour, 1 min, 1 sec")
        self.assertEqual(report_display_duration(0), "")

    def test_create_opens_first_stage_duration(self):
        """Given a new ticket with a stage and a team
        When it is created
        Then one open duration is registered for that stage and team."""
        durations = self.ticket.stage_duration_ids
        self.assertEqual(len(durations), 1)
        self.assertEqual(durations.stage_id, self.stage_new)
        self.assertEqual(durations.team_id, self.team)
        self.assertFalse(durations.end_date)

    def test_stage_change_closes_previous_and_opens_next(self):
        """Given a ticket in stage New
        When the stage changes to Done
        Then New is closed and Done is open."""
        self.ticket.write({"stage_id": self.stage_done.id})
        durations = self.ticket.stage_duration_ids
        self.assertEqual(len(durations), 2)
        closed = durations.filtered(lambda d: d.stage_id == self.stage_new)
        running = durations.filtered(lambda d: d.stage_id == self.stage_done)
        self.assertTrue(closed.end_date)
        self.assertFalse(running.end_date)

    def test_other_writes_do_not_open_durations(self):
        """Given a ticket with one open duration
        When a non stage field is changed
        Then no new duration is created."""
        self.ticket.write({"name": "Renamed"})
        self.assertEqual(len(self.ticket.stage_duration_ids), 1)

    def test_ticket_without_team(self):
        """Given a ticket created without a team
        When it is created and changes stage
        Then it does not break and durations are tracked without team."""
        ticket = self.Ticket.create(
            {"name": "No team", "description": "d", "stage_id": self.stage_new.id}
        )
        self.assertFalse(ticket.team_id)
        self.assertEqual(len(ticket.stage_duration_ids), 1)
        ticket.write({"stage_id": self.stage_wip.id})
        self.assertEqual(len(ticket.stage_duration_ids), 2)
        self.assertFalse(ticket.stage_duration_ids.team_id)

    def test_duration_seconds_for_closed_stage(self):
        """Given a duration with start and end 90061 seconds apart
        When computed
        Then seconds and the display text are exact."""
        start = fields.Datetime.now() - timedelta(days=2)
        dur = self.Duration.create(
            {
                "ticket_id": self.ticket.id,
                "stage_id": self.stage_wip.id,
                "team_id": self.team.id,
                "start_date": start,
                "end_date": start + timedelta(seconds=90061),
            }
        )
        self.assertEqual(dur.duration_seconds, 90061)
        self.assertEqual(dur.duration_display, "1 day, 1 hour, 1 min, 1 sec")

    def test_running_duration_is_marked_in_progress(self):
        """Given a duration without end date started 2 hours ago
        When computed
        Then it counts until now and shows 'em andamento'."""
        dur = self.Duration.create(
            {
                "ticket_id": self.ticket.id,
                "stage_id": self.stage_wip.id,
                "team_id": self.team.id,
                "start_date": fields.Datetime.now() - timedelta(hours=2),
            }
        )
        self.assertGreaterEqual(dur.duration_seconds, 7200)
        self.assertTrue(dur.duration_display.startswith("2 hours"))
        self.assertTrue(dur.duration_display.endswith("(em andamento)"))

    def test_zero_duration_has_empty_display(self):
        """Given a closed duration with the same start and end
        When computed
        Then the display text is empty."""
        now = fields.Datetime.now()
        dur = self.Duration.create(
            {
                "ticket_id": self.ticket.id,
                "stage_id": self.stage_wip.id,
                "team_id": self.team.id,
                "start_date": now,
                "end_date": now,
            }
        )
        self.assertEqual(dur.duration_seconds, 0)
        self.assertFalse(dur.duration_display)

    def test_current_stage_total_sums_all_visits(self):
        """Given a ticket that visited the same stage twice
        When the total time in current stage is read
        Then it sums the closed visit and the running one."""
        ticket = self._ticket()
        now = fields.Datetime.now()
        ticket.stage_duration_ids.unlink()
        for start, end in (
            (now - timedelta(hours=5), now - timedelta(hours=4)),
            (now - timedelta(hours=1), False),
        ):
            self.Duration.create(
                {
                    "ticket_id": ticket.id,
                    "stage_id": self.stage_new.id,
                    "team_id": self.team.id,
                    "start_date": start,
                    "end_date": end,
                }
            )
        ticket.invalidate_recordset()
        self.assertEqual(ticket.current_stage_total_duration, "2 hours")

    def test_current_stage_total_empty_without_history(self):
        """Given a ticket whose history was removed
        When the total time is read
        Then it is empty."""
        ticket = self._ticket()
        ticket.stage_duration_ids.unlink()
        ticket.invalidate_recordset()
        self.assertEqual(ticket.current_stage_total_duration, "")

    def test_deleting_ticket_removes_durations(self):
        """Given a ticket with durations
        When the ticket is deleted
        Then its durations are cascade deleted."""
        ticket = self._ticket()
        ids = ticket.stage_duration_ids.ids
        self.assertTrue(ids)
        ticket.unlink()
        self.assertFalse(self.Duration.search([("id", "in", ids)]))

    def test_helpdesk_user_can_move_ticket(self):
        """Given a helpdesk user (not admin)
        When he changes the stage of a ticket
        Then the duration records are written under his access rights."""
        user = self.env["res.users"].create(
            {
                "name": "LC helpdesk user",
                "login": "lc_helpdesk_user",
                "groups_id": [
                    (6, 0, self.env.ref("helpdesk_mgmt.group_helpdesk_user").ids),
                    (4, self.env.ref("base.group_user").id),
                ],
            }
        )
        ticket = self._ticket().with_user(user)
        ticket.write({"stage_id": self.stage_wip.id})
        self.assertEqual(len(ticket.sudo().stage_duration_ids), 2)

    def _user(self, login, *groups):
        return (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "groups_id": [(6, 0, [self.env.ref(g).id for g in groups])],
                }
            )
        )

    def test_personal_helpdesk_user_records_and_reads_history(self):
        """Given a helpdesk user limited to his own tickets
        When he creates a ticket and moves its stage
        Then the history is recorded and he can read it on the ticket."""
        user = self._user("lc_own_user", "helpdesk_mgmt.group_helpdesk_user_own")
        ticket = self.Ticket.with_user(user).create(
            {
                "name": "Own ticket",
                "description": "d",
                "team_id": self.team.id,
                "stage_id": self.stage_new.id,
                "user_id": user.id,
            }
        )
        ticket.write({"stage_id": self.stage_wip.id})
        durations = ticket.stage_duration_ids
        self.assertEqual(durations.mapped("stage_id"), self.stage_wip | self.stage_new)
        self.assertEqual(len(durations.filtered(lambda d: not d.end_date)), 1)

    def test_helpdesk_user_cannot_forge_history(self):
        """Given a helpdesk user that is not a manager
        When he tries to create, edit or delete a duration directly
        Then access is denied; only helpdesk managers manage the history."""
        user = self._user("lc_forger", "helpdesk_mgmt.group_helpdesk_user")
        duration = self.ticket.stage_duration_ids.with_user(user)
        self.assertTrue(duration.read(["stage_id"]))
        with self.assertRaises(AccessError):
            self.Duration.with_user(user).create(
                {
                    "ticket_id": self.ticket.id,
                    "stage_id": self.stage_done.id,
                    "start_date": fields.Datetime.now(),
                }
            )
        with self.assertRaises(AccessError):
            duration.write({"start_date": fields.Datetime.now() - timedelta(days=9)})
        with self.assertRaises(AccessError):
            duration.unlink()
        manager = self._user("lc_manager", "helpdesk_mgmt.group_helpdesk_manager")
        for operation in ("read", "write", "create", "unlink"):
            with self.subTest(operation=operation):
                self.assertTrue(
                    self.Duration.with_user(manager).check_access_rights(
                        operation, raise_exception=False
                    )
                )

    def test_outsiders_cannot_read_history_or_report(self):
        """Given an internal user outside the helpdesk groups and a portal user
        Then neither of them reads the durations or the report."""
        internal = self._user("lc_internal", "base.group_user")
        portal = self._user("lc_portal", "base.group_portal")
        models = (
            "helpdesk.ticket.stage.duration",
            "helpdesk.ticket.stage.duration.report",
        )
        for user in (internal, portal):
            for model in models:
                with self.subTest(user=user.login, model=model):
                    self.assertFalse(
                        self.env[model]
                        .with_user(user)
                        .check_access_rights("read", raise_exception=False)
                    )

    def test_report_aggregates_per_team_and_stage(self):
        """Given tickets that stayed in a stage for known periods
        When the report is read
        Then counts, min, max, average and completion rate match."""
        team = self.env["helpdesk.ticket.team"].create({"name": "LC Report team"})
        stage = self.env["helpdesk.ticket.stage"].create({"name": "LC Report stage"})
        # The report measures open stages with SQL NOW(), the transaction start.
        now = self.env.cr.now()
        for hours, closed in ((1, True), (3, True), (2, False)):
            ticket = self._ticket(team_id=team.id, stage_id=stage.id)
            ticket.stage_duration_ids.write(
                {
                    "start_date": now - timedelta(hours=hours),
                    "end_date": now if closed else False,
                }
            )
        self.env.flush_all()
        row = self.env["helpdesk.ticket.stage.duration.report"].search(
            [("team_id", "=", team.id), ("stage_id", "=", stage.id)]
        )
        self.assertEqual(len(row), 1)
        self.assertEqual(row.ticket_count, 3)
        self.assertEqual(row.completed_tickets, 2)
        self.assertEqual(row.active_tickets, 1)
        self.assertAlmostEqual(row.completion_rate, 200 / 3, places=3)
        self.assertEqual(row.min_duration_seconds, 3600)
        self.assertGreaterEqual(row.max_duration_seconds, 10800)
        self.assertGreaterEqual(row.total_duration_seconds, 3600 + 10800 + 7200)
        self.assertTrue(row.avg_duration_display)

    def test_report_display_empty_without_average(self):
        """Given a report record without average
        When the display is computed
        Then it is empty."""
        report = self.env["helpdesk.ticket.stage.duration.report"].new(
            {"avg_duration_seconds": 0}
        )
        self.assertEqual(report.avg_duration_display, "")
        report.avg_duration_seconds = 3600
        self.assertEqual(report.avg_duration_display, "1 hour")

    def test_views_show_tracking(self):
        """Given the ticket form and the report views
        When rendered
        Then the stage duration list and the report fields are visible."""
        arch = etree.fromstring(self.Ticket.get_view(view_type="form")["arch"])
        self.assertTrue(arch.xpath("//field[@name='stage_duration_ids']"))
        kanban = self.Ticket.get_view(view_type="kanban")["arch"]
        self.assertIn("current_stage_total_duration", kanban)
        report = self.env["helpdesk.ticket.stage.duration.report"]
        for vtype in ("tree", "pivot", "graph", "kanban", "search"):
            view = report.get_view(view_type=vtype)
            self.assertIn("<field", view["arch"], vtype)
