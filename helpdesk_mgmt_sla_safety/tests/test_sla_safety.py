# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from freezegun import freeze_time
from lxml import etree

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

# The 24x7 calendar ends each day at 23:59:59.999999, so a deadline that
# crosses midnight drifts by microseconds. Fixed dates keep it deterministic.
CREATE_DATE = datetime(2026, 1, 7, 8, 0, 0)
NOW = "2026-01-07 08:05:00"


@freeze_time(NOW)
@tagged("post_install", "-at_install")
class TestSlaSafety(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.Sla = cls.env["helpdesk.sla"]
        # 24x7 calendar makes the planning deterministic
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "24x7 safety test",
                "tz": "UTC",
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "day %s" % d,
                            "dayofweek": str(d),
                            "hour_from": 0,
                            "hour_to": 24,
                        },
                    )
                    for d in range(7)
                ],
            }
        )
        cls.team = cls.env["helpdesk.ticket.team"].create(
            {
                "name": "Safety team",
                "use_sla": True,
                "resource_calendar_id": cls.calendar.id,
            }
        )
        cls.ticket = cls.Ticket.create(
            {"name": "T", "description": "d", "team_id": cls.team.id}
        )
        cls.env.cr.execute(
            "UPDATE helpdesk_ticket SET create_date=%s WHERE id=%s",
            (CREATE_DATE, cls.ticket.id),
        )
        cls.ticket.invalidate_recordset()

    def _sla(self, **kw):
        vals = {"name": "SLA safety", "team_ids": [(6, 0, self.team.ids)]}
        vals.update(kw)
        return self.Sla.create(vals)

    def _set_create_date(self, ticket, delta):
        new = fields.Datetime.now() + delta
        self.env.cr.execute(
            "UPDATE helpdesk_ticket SET create_date=%s WHERE id=%s",
            (new, ticket.id),
        )
        ticket.invalidate_recordset()

    def test_defaults_are_zero(self):
        """Given a new SLA
        When no safety values are given
        Then safety days and hours default to zero."""
        sla = self._sla()
        self.assertEqual((sla.safety_days, sla.safety_hours), (0, 0))

    def test_safety_hours_define_safety_deadline(self):
        """Given an SLA with 2 safety hours and a 24x7 calendar
        When the SLA is checked
        Then the safety deadline is create_date + 2 hours."""
        sla = self._sla(hours=10, safety_hours=2)
        sla.check_ticket_sla(self.ticket)
        self.assertEqual(
            self.ticket.sla_safety_deadline,
            self.ticket.create_date + timedelta(hours=2),
        )
        self.assertFalse(self.ticket.sla_safety_alert)

    def test_standard_sla_deadline_is_still_computed(self):
        """Given an SLA with hours and safety hours
        When the SLA is checked
        Then the standard SLA deadline is also set by the parent logic."""
        sla = self._sla(hours=10, safety_hours=2)
        sla.check_ticket_sla(self.ticket)
        self.assertEqual(
            self.ticket.sla_deadline, self.ticket.create_date + timedelta(hours=10)
        )

    def test_safety_days_postpone_the_safety_deadline(self):
        """Given two SLAs differing by one safety day
        When both are checked on the same ticket
        Then the safety deadline moves one day later."""
        self._sla(safety_days=1, safety_hours=1).check_ticket_sla(self.ticket)
        one_day = self.ticket.sla_safety_deadline
        self._sla(safety_days=2, safety_hours=1).check_ticket_sla(self.ticket)
        two_days = self.ticket.sla_safety_deadline
        self.assertEqual(two_days - one_day, timedelta(days=1))
        self.assertGreater(one_day, self.ticket.create_date + timedelta(days=1))

    def test_alert_when_safety_deadline_is_past(self):
        """Given a ticket created long ago
        When the SLA with 1 safety hour is checked
        Then the safety alert is raised."""
        self._set_create_date(self.ticket, timedelta(days=-2))
        self._sla(hours=100, safety_hours=1).check_ticket_sla(self.ticket)
        self.assertTrue(self.ticket.sla_safety_alert)

    def test_no_alert_when_safety_deadline_is_future(self):
        """Given a fresh ticket
        When the SLA with 5 safety hours is checked
        Then there is no safety alert."""
        self._sla(hours=100, safety_hours=5).check_ticket_sla(self.ticket)
        self.assertFalse(self.ticket.sla_safety_alert)

    def test_alert_follows_safety_deadline_field(self):
        """Given a ticket without safety deadline
        When the deadline is set in the past, in the future and cleared
        Then the alert is True, False and False respectively."""
        ticket = self.ticket
        self.assertFalse(ticket.sla_safety_alert)
        ticket.sla_safety_deadline = fields.Datetime.now() - timedelta(hours=1)
        self.assertTrue(ticket.sla_safety_alert)
        ticket.sla_safety_deadline = fields.Datetime.now() + timedelta(hours=1)
        self.assertFalse(ticket.sla_safety_alert)
        ticket.sla_safety_deadline = False
        self.assertFalse(ticket.sla_safety_alert)

    def test_cron_sets_safety_deadline(self):
        """Given an open ticket and a safety SLA on its team
        When the SLA scheduler runs
        Then the ticket gets a safety deadline."""
        self.Sla.search([]).write({"active": False})
        self._sla(hours=10, safety_hours=3)
        self.Sla.check_sla()
        self.assertEqual(
            self.ticket.sla_safety_deadline,
            self.ticket.create_date + timedelta(hours=3),
        )

    def test_views_show_safety_fields(self):
        """Given the ticket and SLA form views
        When they are rendered
        Then the safety fields are present."""
        tarch = etree.fromstring(self.Ticket.get_view(view_type="form")["arch"])
        self.assertTrue(tarch.xpath("//field[@name='sla_safety_deadline']"))
        self.assertTrue(tarch.xpath("//field[@name='sla_safety_alert']"))
        sarch = etree.fromstring(self.Sla.get_view(view_type="form")["arch"])
        self.assertTrue(sarch.xpath("//field[@name='safety_days']"))
        self.assertTrue(sarch.xpath("//field[@name='safety_hours']"))
