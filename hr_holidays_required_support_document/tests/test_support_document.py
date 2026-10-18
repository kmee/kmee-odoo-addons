# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSupportDocument(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, mail_notrack=True)
        )
        cls.employee = cls.env["hr.employee"].create({"name": "Support Employee"})
        cls.work_entry_type = cls.env["hr.work.entry.type"].create(
            {
                "name": "Medical leave",
                "code": "MEDLEAVE",
                "requires_allocation": False,
                "support_document": True,
                "required_support_document": True,
            }
        )

    def _leave_vals(self, work_entry_type):
        return {
            "employee_id": self.employee.id,
            "work_entry_type_id": work_entry_type.id,
            "request_date_from": "2026-03-02",
            "request_date_to": "2026-03-02",
        }

    def test_leave_without_document_is_blocked(self):
        with self.assertRaises(ValidationError):
            self.env["hr.leave"].create(self._leave_vals(self.work_entry_type))

    def test_leave_type_without_requirement_is_allowed(self):
        self.work_entry_type.required_support_document = False
        leave = self.env["hr.leave"].create(self._leave_vals(self.work_entry_type))
        self.assertTrue(leave)
