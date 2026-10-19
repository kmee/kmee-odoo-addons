# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMailRoleFilter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.role = cls.env["res.users.role"].create({"name": "Notified role"})
        cls.role2 = cls.env["res.users.role"].create({"name": "Other role"})
        cls.user_with_role = Users.create(
            {
                "name": "With role",
                "login": "with_role",
                "email": "with_role@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
                "role_line_ids": [(0, 0, {"role_id": cls.role.id})],
            }
        )
        cls.user_both_roles = Users.create(
            {
                "name": "Both roles",
                "login": "both_roles",
                "email": "both_roles@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
                "role_line_ids": [
                    (0, 0, {"role_id": cls.role.id}),
                    (0, 0, {"role_id": cls.role2.id}),
                ],
            }
        )
        cls.user_without_role = Users.create(
            {
                "name": "Without role",
                "login": "without_role",
                "email": "without_role@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.record = cls.env["res.partner"].create({"name": "Record"})
        cls.model = cls.env["ir.model"]._get("res.partner")
        cls.other_model = cls.env["ir.model"]._get("res.partner.category")
        cls.partners = (
            cls.user_with_role.partner_id
            | cls.user_both_roles.partner_id
            | cls.user_without_role.partner_id
        )

    def _recipient_ids(self, record=None):
        record = record or self.record
        message = record.message_post(body="Hello", partner_ids=self.partners.ids)
        data = record._notify_get_recipients(message, {})
        return [d["id"] for d in data]

    def _filter(self, role=None, model=None, **kw):
        vals = {
            "role_id": (role or self.role).id,
            "model_id": (model or self.model).id,
        }
        vals.update(kw)
        return self.env["mail.role.filter"].create(vals)

    def test_no_filter_keeps_recipients(self):
        """Given no filter configured for the model
        When a message is posted to three users
        Then all of them are notified."""
        ids = self._recipient_ids()
        self.assertEqual(set(ids), set(self.partners.ids))

    def test_filter_keeps_only_users_with_role(self):
        """Given a filter for a role on res.partner
        When a message is posted to users with and without the role
        Then only users holding the role are notified."""
        self._filter()
        ids = self._recipient_ids()
        self.assertIn(self.user_with_role.partner_id.id, ids)
        self.assertIn(self.user_both_roles.partner_id.id, ids)
        self.assertNotIn(self.user_without_role.partner_id.id, ids)

    def test_user_matching_two_filtered_roles_is_notified_once(self):
        """Given two filters (two roles) for the same model
        When a user holds both roles
        Then it appears once in the recipients."""
        self._filter()
        self._filter(role=self.role2)
        ids = self._recipient_ids()
        self.assertEqual(ids.count(self.user_both_roles.partner_id.id), 1)
        self.assertNotIn(self.user_without_role.partner_id.id, ids)

    def test_inactive_filter_is_ignored(self):
        """Given an archived filter
        When a message is posted
        Then nobody is filtered out."""
        self._filter(active=False)
        self.assertIn(self.user_without_role.partner_id.id, self._recipient_ids())

    def test_filter_for_other_model_does_not_apply(self):
        """Given a filter configured for another model
        When a message is posted on res.partner
        Then recipients are untouched."""
        self._filter(model=self.other_model)
        self.assertIn(self.user_without_role.partner_id.id, self._recipient_ids())

    def test_filter_applies_to_the_configured_model(self):
        """Given a filter for res.partner.category
        When a message is posted on a category record
        Then users without the role are removed there."""
        self._filter(model=self.other_model)
        category = self.env["res.partner.category"].create({"name": "Cat"})
        ids = self._recipient_ids(category)
        self.assertNotIn(self.user_without_role.partner_id.id, ids)
        self.assertIn(self.user_with_role.partner_id.id, ids)

    def test_partner_without_user_is_removed_by_filter(self):
        """Given a filter and a recipient that is not a user
        When a message is posted
        Then that recipient is dropped."""
        self._filter()
        plain = self.env["res.partner"].create({"name": "Plain", "email": "p@e.com"})
        message = self.record.message_post(
            body="Hi", partner_ids=(self.partners | plain).ids
        )
        ids = [d["id"] for d in self.record._notify_get_recipients(message, {})]
        self.assertNotIn(plain.id, ids)
        self.assertIn(self.user_with_role.partner_id.id, ids)

    def test_filter_cascades_with_role_deletion(self):
        """Given a filter on a role
        When the role is deleted
        Then the filter is removed (ondelete cascade)."""
        role = self.env["res.users.role"].create({"name": "Temp"})
        rule = self._filter(role=role)
        role.unlink()
        self.assertFalse(rule.exists())
