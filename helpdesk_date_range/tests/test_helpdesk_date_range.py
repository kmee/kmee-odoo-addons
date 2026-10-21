# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.osv import expression
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install")
class TestHelpdeskDateRange(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        DateRangeType = cls.env["date.range.type"]
        DateRange = cls.env["date.range"]
        cls.type_month = DateRangeType.create({"name": "Test Month HDR"})
        cls.type_old = DateRangeType.create({"name": "Test Old HDR"})
        cls.range_jan = DateRange.create(
            {
                "name": "2030-01",
                "date_start": "2030-01-01",
                "date_end": "2030-01-31",
                "type_id": cls.type_month.id,
            }
        )
        cls.range_feb = DateRange.create(
            {
                "name": "2030-02",
                "date_start": "2030-02-01",
                "date_end": "2030-02-28",
                "type_id": cls.type_month.id,
            }
        )
        cls.range_old = DateRange.create(
            {
                "name": "2029-12",
                "date_start": "2029-12-01",
                "date_end": "2029-12-31",
                "type_id": cls.type_old.id,
            }
        )
        cls.type_old.active = False
        cls.Ticket = cls.env["helpdesk.ticket"]
        # a team keeps the tests valid when stage tracking modules are installed
        cls.team = cls.env["helpdesk.ticket.team"].create({"name": "Date range team"})
        cls.ticket_jan = cls.Ticket.create(
            {
                "name": "Jan ticket",
                "description": "d",
                "team_id": cls.team.id,
                "date_range_id": cls.range_jan.id,
            }
        )
        cls.ticket_feb = cls.Ticket.create(
            {
                "name": "Feb ticket",
                "description": "d",
                "team_id": cls.team.id,
                "date_range_id": cls.range_feb.id,
            }
        )
        cls.ticket_none = cls.Ticket.create(
            {"name": "No period", "description": "d", "team_id": cls.team.id}
        )

    def test_ticket_stores_reference_period(self):
        """Given a ticket with no period
        When the user sets a date range
        Then the ticket keeps it and the default is empty."""
        self.assertFalse(self.ticket_none.date_range_id)
        self.ticket_none.date_range_id = self.range_jan
        self.ticket_none.invalidate_recordset()
        self.assertEqual(self.ticket_none.date_range_id, self.range_jan)

    def test_search_tickets_by_reference_period(self):
        """Given tickets in different periods
        When searching by date_range_id
        Then only the tickets of that period are returned."""
        found = self.Ticket.search([("date_range_id", "=", self.range_jan.id)])
        self.assertIn(self.ticket_jan, found)
        self.assertNotIn(self.ticket_feb, found)
        self.assertNotIn(self.ticket_none, found)

    def test_group_by_reference_period(self):
        """Given tickets in two periods and one without
        When grouping by date_range_id
        Then there is one group per period with the right counts."""
        domain = [
            ("id", "in", (self.ticket_jan + self.ticket_feb + self.ticket_none).ids)
        ]
        groups = self.Ticket.read_group(
            domain, ["date_range_id"], ["date_range_id"], lazy=False
        )
        counts = {
            (g["date_range_id"] and g["date_range_id"][0]): g["__count"] for g in groups
        }
        self.assertEqual(
            counts,
            {self.range_jan.id: 1, self.range_feb.id: 1, False: 1},
        )

    def test_field_domain_excludes_inactive_types(self):
        """Given a period whose type was archived
        When evaluating the field domain
        Then the period is not selectable but active ones are."""
        domain = safe_eval(self.Ticket._fields["date_range_id"].domain)
        selectable = self.env["date.range"].search(
            expression.AND(
                [domain, [("id", "in", (self.range_jan + self.range_old).ids)]]
            )
        )
        self.assertIn(self.range_jan, selectable)
        self.assertNotIn(self.range_old, selectable)

    def test_form_view_shows_reference_period(self):
        """Given the ticket form view
        When it is rendered
        Then it contains the date_range_id field after the creation date."""
        arch = self.Ticket.get_view(view_type="form")["arch"]
        node = etree.fromstring(arch).xpath("//field[@name='date_range_id']")
        self.assertEqual(len(node), 1)

    def test_search_view_has_filter_and_group_by(self):
        """Given the ticket search view
        When it is rendered
        Then it has the date_range_id field and the group by filter."""
        arch = etree.fromstring(self.Ticket.get_view(view_type="search")["arch"])
        self.assertTrue(arch.xpath("//field[@name='date_range_id']"))
        group = arch.xpath("//filter[@name='date_range_id']")
        self.assertTrue(group)
        self.assertIn("date_range_id", group[0].get("context"))
