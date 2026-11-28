# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestMrpProductionRequestApproval(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.request = cls.env.ref(
            "mrp_production_request_approval.mrp_production_request_demo_approval"
        )
        cls.approver = cls.env.ref(
            "mrp_production_request_approval.user_aprovador_producao"
        )
        manager_group = cls.env.ref(
            "mrp_production_request.group_mrp_production_request_manager"
        )
        cls.other_manager = cls.env["res.users"].create(
            {
                "name": "Camila Duarte Pinheiro",
                "login": "camila.pinheiro.producao",
                "groups_id": [(6, 0, [manager_group.id])],
            }
        )

    def test_only_approver_approves_and_reopens(self):
        with self.assertRaises(UserError):
            self.request.with_user(self.other_manager).button_approved()
        self.request.with_user(self.approver).button_approved()
        self.assertEqual(self.request.state, "approved")
        self.assertEqual(self.request.approved_by, self.approver)
        self.assertTrue(self.request.approved_datetime)
        self.request.button_done()
        with self.assertRaises(UserError):
            self.request.with_user(self.other_manager).button_reopen()
        self.request.with_user(self.approver).button_reopen()
        self.assertEqual(self.request.state, "approved")

    def test_without_approvers_any_manager_approves(self):
        self.request.assigned_to_ids = False
        self.request.with_user(self.other_manager).button_approved()
        self.assertEqual(self.request.approved_by, self.other_manager)
