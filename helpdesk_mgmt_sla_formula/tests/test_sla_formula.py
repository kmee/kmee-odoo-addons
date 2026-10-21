# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from lxml import etree

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestSlaFormula(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Sla = cls.env["helpdesk.sla"]
        cls.team = cls.env["helpdesk.ticket.team"].create(
            {"name": "Formula team", "use_sla": True}
        )
        cls.ticket = cls.env["helpdesk.ticket"].create(
            {"name": "T", "description": "d", "team_id": cls.team.id}
        )

    def _sla(self, formula, use_formula=True, **kw):
        vals = {
            "name": "SLA formula",
            "team_ids": [(6, 0, self.team.ids)],
            "use_formula": use_formula,
            "sla_deadline_formula": formula,
        }
        vals.update(kw)
        return self.Sla.create(vals)

    def test_invalid_syntax_is_rejected(self):
        """Given an SLA using the formula
        When the formula has a syntax error
        Then a ValidationError is raised."""
        with self.assertRaises(ValidationError):
            self._sla("record.create_date +")

    def test_invalid_syntax_is_ignored_when_formula_is_off(self):
        """Given an SLA that does not use the formula
        When it stores a broken formula
        Then it is accepted (only active formulas are validated)."""
        sla = self._sla("record.create_date +", use_formula=False)
        self.assertTrue(sla.id)

    def test_empty_formula_is_accepted(self):
        """Given an SLA using the formula
        When the formula is empty
        Then the constraint does not complain."""
        self.assertTrue(self._sla(False).id)

    def test_syntax_error_on_write_is_rejected(self):
        """Given a valid formula SLA
        When the formula is rewritten with invalid code
        Then a ValidationError is raised."""
        sla = self._sla("record.create_date")
        with self.assertRaises(ValidationError):
            sla.sla_deadline_formula = "def ("

    def test_formula_defines_deadline_in_the_future(self):
        """Given a formula returning create_date + 2 days
        When the SLA is checked on a ticket
        Then the deadline is that date and the ticket is not expired."""
        sla = self._sla("record.create_date + timedelta(days=2)")
        sla.check_ticket_sla(self.ticket)
        self.assertEqual(
            self.ticket.sla_deadline, self.ticket.create_date + timedelta(days=2)
        )
        self.assertFalse(self.ticket.sla_expired)

    def test_formula_in_the_past_expires_ticket(self):
        """Given a formula returning a past date
        When the SLA is checked
        Then the ticket is flagged as expired."""
        sla = self._sla("record.create_date - timedelta(days=1)")
        sla.check_ticket_sla(self.ticket)
        self.assertEqual(
            self.ticket.sla_deadline, self.ticket.create_date - timedelta(days=1)
        )
        self.assertTrue(self.ticket.sla_expired)

    def test_formula_has_relativedelta_and_datetime(self):
        """Given a formula using relativedelta and datetime
        When the SLA is checked
        Then both names are available in the formula namespace."""
        sla = self._sla(
            "datetime(2099, 1, 31) + relativedelta(months=1)",
        )
        sla.check_ticket_sla(self.ticket)
        self.assertEqual(
            fields.Datetime.to_datetime(self.ticket.sla_deadline).date().isoformat(),
            "2099-02-28",
        )
        self.assertFalse(self.ticket.sla_expired)

    def test_formula_returning_date_is_supported(self):
        """Given the help text promises datetime or date
        When the formula returns a plain date
        Then the deadline is stored and expiry is computed."""
        sla = self._sla("record.create_date.date() + timedelta(days=3)")
        sla.check_ticket_sla(self.ticket)
        self.assertTrue(self.ticket.sla_deadline)
        self.assertFalse(self.ticket.sla_expired)

    def test_formula_error_is_logged_and_ticket_untouched(self):
        """Given a formula referencing an unknown name
        When the SLA is checked
        Then the error is logged and the ticket keeps its previous values."""
        sla = self._sla("unknown_name + 1")
        self.assertFalse(self.ticket.sla_deadline)
        with self.assertLogs(
            "odoo.addons.helpdesk_mgmt_sla_formula.models.helpdesk_sla", "ERROR"
        ) as logs:
            sla.check_ticket_sla(self.ticket)
        self.assertIn("Erro ao calcular deadline SLA", logs.output[0])
        self.assertFalse(self.ticket.sla_deadline)
        self.assertFalse(self.ticket.sla_expired)

    def test_formula_cannot_import_modules(self):
        """Given a formula trying to import os
        When the SLA is saved
        Then it is rejected before it can ever run."""
        with self.assertRaises(ValidationError):
            self._sla("__import__('os').getcwd()")

    def test_formula_cannot_reach_the_orm(self):
        """Given a formula that goes from the ticket to the environment
        When the SLA is checked (the scheduler runs it as superuser)
        Then the ORM is not reachable and nothing is written."""
        sla = self._sla(
            "record.create_date"
            " + timedelta(days=record.env['res.users'].search_count([]))"
        )
        with self.assertLogs(
            "odoo.addons.helpdesk_mgmt_sla_formula.models.helpdesk_sla", "ERROR"
        ):
            sla.check_ticket_sla(self.ticket)
        self.assertFalse(self.ticket.sla_deadline)

    def test_formula_cannot_write_through_the_record(self):
        """Given a formula that calls a method of the ticket
        When the SLA is checked
        Then the method is not reachable and the ticket is unchanged."""
        sla = self._sla("record.write({'name': 'changed'}) or record.create_date")
        with self.assertLogs(
            "odoo.addons.helpdesk_mgmt_sla_formula.models.helpdesk_sla", "ERROR"
        ):
            sla.check_ticket_sla(self.ticket)
        self.assertEqual(self.ticket.name, "T")
        self.assertFalse(self.ticket.sla_deadline)

    def test_formula_reads_related_fields(self):
        """Given a formula reading a field through a many2one of the ticket
        When the SLA is checked
        Then field values are still available to the formula."""
        sla = self._sla("record.create_date + timedelta(days=len(record.team_id.name))")
        sla.check_ticket_sla(self.ticket)
        self.assertEqual(
            self.ticket.sla_deadline,
            self.ticket.create_date + timedelta(days=len("Formula team")),
        )

    def test_formula_fields_are_restricted_to_helpdesk_managers(self):
        """Given a helpdesk user that another module allowed to edit SLAs
        When he writes the formula fields
        Then the server refuses, while a helpdesk manager can do it."""
        user = new_test_user(
            self.env,
            login="sla_formula_user",
            groups="base.group_user,helpdesk_mgmt.group_helpdesk_user",
        )
        manager = new_test_user(
            self.env,
            login="sla_formula_manager",
            groups="base.group_user,helpdesk_mgmt.group_helpdesk_manager",
        )
        self.env["ir.model.access"].create(
            {
                "name": "helpdesk sla user write (test)",
                "model_id": self.env["ir.model"]._get_id("helpdesk.sla"),
                "group_id": self.env.ref("helpdesk_mgmt.group_helpdesk_user").id,
                "perm_read": True,
                "perm_write": True,
            }
        )
        sla = self._sla("record.create_date")
        # control: the user can edit the SLA itself
        sla.with_user(user).write({"name": "Renamed by user"})
        self.assertEqual(sla.name, "Renamed by user")
        for vals in (
            {"sla_deadline_formula": "record.create_date + timedelta(days=1)"},
            {"use_formula": False},
        ):
            with self.assertRaises(AccessError):
                sla.with_user(user).write(vals)
        sla.with_user(manager).write(
            {"sla_deadline_formula": "record.create_date + timedelta(days=1)"}
        )
        self.assertEqual(
            sla.sla_deadline_formula, "record.create_date + timedelta(days=1)"
        )

    def test_without_formula_falls_back_to_standard_delay(self):
        """Given an SLA with hours but without formula
        When the SLA is checked
        Then the standard calendar based deadline is computed."""
        sla = self._sla("record.create_date - timedelta(days=100)", use_formula=False)
        sla.write({"hours": 1})
        sla.check_ticket_sla(self.ticket)
        self.assertTrue(self.ticket.sla_deadline)
        # the formula was ignored: the deadline is not 100 days in the past
        self.assertGreater(self.ticket.sla_deadline, self.ticket.create_date)

    def test_cron_applies_formula_sla(self):
        """Given an open ticket and a formula SLA on its team
        When the SLA scheduler runs
        Then the ticket gets the formula deadline."""
        self.Sla.search([]).write({"active": False})
        self._sla("record.create_date + timedelta(hours=5)")
        self.Sla.check_sla()
        self.assertEqual(
            self.ticket.sla_deadline, self.ticket.create_date + timedelta(hours=5)
        )

    def test_sla_form_view_has_formula_fields(self):
        """Given the SLA form view
        When it is rendered
        Then use_formula and the formula field are present and days is hidden by it."""
        arch = etree.fromstring(self.Sla.get_view(view_type="form")["arch"])
        self.assertTrue(arch.xpath("//field[@name='use_formula']"))
        self.assertTrue(arch.xpath("//field[@name='sla_deadline_formula']"))
        days = arch.xpath("//field[@name='days']")[0]
        self.assertIn("use_formula", days.get("modifiers", ""))
