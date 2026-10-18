# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged

from ..models.helpdesk_ticket_track import display_duration


@tagged("post_install", "-at_install")
class TestStageDuration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.stage_new = cls.env["helpdesk.ticket.stage"].create({"name": "New"})
        cls.stage_done = cls.env["helpdesk.ticket.stage"].create({"name": "Done"})
        cls.team = cls.env["helpdesk.ticket.team"].create({"name": "Team"})
        cls.ticket = cls.env["helpdesk.ticket"].create(
            {
                "name": "Ticket",
                "description": "Description",
                "team_id": cls.team.id,
                "stage_id": cls.stage_new.id,
            }
        )

    def test_display_duration(self):
        self.assertEqual(display_duration(90061, 3), "1 day, 1 hour, 1 min")
        self.assertEqual(display_duration(0), "")

    def test_stage_change_tracks_durations(self):
        durations = self.ticket.stage_duration_ids
        self.assertEqual(len(durations), 1)
        self.assertEqual(durations.stage_id, self.stage_new)
        self.assertFalse(durations.end_date)
        self.ticket.write({"stage_id": self.stage_done.id})
        durations = self.ticket.stage_duration_ids
        self.assertEqual(len(durations), 2)
        closed = durations.filtered(lambda d: d.stage_id == self.stage_new)
        self.assertTrue(closed.end_date)
        running = durations.filtered(lambda d: d.stage_id == self.stage_done)
        self.assertFalse(running.end_date)
