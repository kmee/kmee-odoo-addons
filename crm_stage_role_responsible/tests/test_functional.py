# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStageRoleResponsible(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {"name": "Closer User", "login": "closer_user_test"}
        )
        cls.stage = cls.env["crm.stage"].create(
            {"name": "Closing", "role_responsible": "closer"}
        )
        cls.default_stage = cls.env["crm.stage"].create({"name": "Plain"})

    def test_default_role(self):
        self.assertEqual(self.default_stage.role_responsible, "default")

    def test_role_requires_user(self):
        with self.assertRaises(UserError):
            self.env["crm.lead"].create(
                {"name": "No closer", "stage_id": self.stage.id}
            )

    def test_role_assigns_user(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "With closer",
                "stage_id": self.stage.id,
                "closer_id": self.user.id,
            }
        )
        self.assertEqual(lead.user_id, self.user)

    def test_write_stage_assigns_user(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Move",
                "stage_id": self.default_stage.id,
                "closer_id": self.user.id,
            }
        )
        lead.write({"stage_id": self.stage.id})
        self.assertEqual(lead.user_id, self.user)

    def test_quotation_context(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Ctx",
                "stage_id": self.default_stage.id,
                "farmer_id": self.user.id,
            }
        )
        ctx = lead._prepare_opportunity_quotation_context()
        self.assertEqual(ctx["default_farmer_id"], self.user.id)
