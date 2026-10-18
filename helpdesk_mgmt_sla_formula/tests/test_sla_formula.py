# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestHelpdeskSlaFormula(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.team = cls.env["helpdesk.ticket.team"].create(
            {"name": "SLA team", "use_sla": True}
        )

    def _ticket(self):
        return self.env["helpdesk.ticket"].create(
            {
                "name": "Ticket",
                "description": "Description",
                "team_id": self.team.id,
            }
        )

    def _sla(self, formula, use_formula=True):
        return self.env["helpdesk.sla"].create(
            {
                "name": "Formula SLA",
                "team_ids": [(6, 0, self.team.ids)],
                "use_formula": use_formula,
                "sla_deadline_formula": formula,
            }
        )

    def test_deadline_from_formula(self):
        self._sla("record.create_date + timedelta(days=2)")
        ticket = self._ticket()
        self.assertEqual(
            ticket.ticket_sla_ids.deadline, ticket.create_date + timedelta(days=2)
        )

    def test_invalid_formula_keeps_standard_deadline(self):
        self._sla("record.unknown_attribute")
        with mute_logger("odoo.addons.helpdesk_mgmt_sla_formula.models.helpdesk_sla"):
            ticket = self._ticket()
            self.assertTrue(ticket.ticket_sla_ids.deadline)

    def test_syntax_error_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._sla("record.create_date +")
