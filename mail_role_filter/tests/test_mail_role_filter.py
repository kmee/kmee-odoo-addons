# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMailRoleFilter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.role = cls.env["res.users.role"].create({"name": "Notified role"})
        cls.user_with_role = cls.env["res.users"].create(
            {
                "name": "With role",
                "login": "with_role",
                "email": "with_role@example.com",
                "role_line_ids": [(0, 0, {"role_id": cls.role.id})],
            }
        )
        cls.user_without_role = cls.env["res.users"].create(
            {
                "name": "Without role",
                "login": "without_role",
                "email": "without_role@example.com",
            }
        )
        cls.record = cls.env["res.partner"].create({"name": "Record"})
        cls.model = cls.env["ir.model"]._get("res.partner")

    def _recipient_ids(self):
        message = self.record.message_post(
            body="Hello",
            partner_ids=[
                self.user_with_role.partner_id.id,
                self.user_without_role.partner_id.id,
            ],
        )
        data = self.record._notify_get_recipients(message, {})
        return {d["id"] for d in data}

    def test_filter_by_role(self):
        self.env["mail.role.filter"].create(
            {"role_id": self.role.id, "model_id": self.model.id}
        )
        ids = self._recipient_ids()
        self.assertIn(self.user_with_role.partner_id.id, ids)
        self.assertNotIn(self.user_without_role.partner_id.id, ids)

    def test_no_filter_keeps_recipients(self):
        ids = self._recipient_ids()
        self.assertIn(self.user_with_role.partner_id.id, ids)
        self.assertIn(self.user_without_role.partner_id.id, ids)
