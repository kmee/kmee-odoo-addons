# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOvertimeAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, no_reset_password=True)
        )
        Users = cls.env["res.users"]
        cls.internal_user = Users.create(
            {
                "name": "Plain internal user",
                "login": "overtime_internal",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.portal_user = Users.create(
            {
                "name": "Portal user",
                "login": "overtime_portal",
                "groups_id": [(6, 0, [cls.env.ref("base.group_portal").id])],
            }
        )
        cls.officer = Users.create(
            {
                "name": "Attendance officer",
                "login": "overtime_officer",
                "groups_id": [
                    (
                        6,
                        0,
                        [cls.env.ref("hr_attendance.group_hr_attendance_officer").id],
                    )
                ],
            }
        )

    def _can(self, user, operation):
        return (
            self.env["hr.attendance.overtime"]
            .with_user(user)
            .check_access_rights(operation, raise_exception=False)
        )

    def test_internal_user_cannot_change_overtime(self):
        """
        Given an internal user outside the attendance groups
        When the access rights on overtime are checked
        Then the module grants no write, create or unlink to that user
        """
        for operation in ("write", "create", "unlink"):
            with self.subTest(operation=operation):
                self.assertFalse(self._can(self.internal_user, operation))

    def test_portal_user_cannot_read_overtime(self):
        """
        Given a portal user
        When the access rights on overtime are checked
        Then the module does not open overtime records to the portal
        """
        for operation in ("read", "write", "create", "unlink"):
            with self.subTest(operation=operation):
                self.assertFalse(self._can(self.portal_user, operation))

    def test_attendance_officer_reads_overtime(self):
        """
        Given an attendance officer
        When the access rights on overtime are checked
        Then the officer can read the records the report prints
        """
        self.assertTrue(self._can(self.officer, "read"))
