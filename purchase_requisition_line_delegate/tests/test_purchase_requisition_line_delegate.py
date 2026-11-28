# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseRequisitionLineDelegate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.vendor = cls.env["res.partner"].create({"name": "Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Product A", "purchase_ok": True}
        )
        cls.other_product = cls.env["product.product"].create(
            {"name": "Product B", "purchase_ok": True}
        )
        cls.req_a = cls._create_requisition(
            [
                (cls.product, 10, date(2025, 3, 10)),
                (cls.other_product, 5, date(2025, 3, 5)),
                (cls.product, 4, date(2025, 3, 1)),
            ]
        )
        cls.req_b = cls._create_requisition([(cls.product, 1, False)])

    @classmethod
    def _create_requisition(cls, lines):
        return cls.env["purchase.requisition"].create(
            {
                "requisition_type": "purchase_template",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": qty,
                            "schedule_date": schedule_date,
                        },
                    )
                    for product, qty, schedule_date in lines
                ],
            }
        )

    def _delegate(self, line, target):
        wizard = self.env["purchase.requisition.delegate"].create(
            {
                "purchase_requisition_id": line.requisition_id.id,
                "purchase_requisition_line_id": line.id,
                "to_purchase_requisition_id": target.id,
            }
        )
        wizard.doit()

    def test_delegate_moves_line(self):
        line = self.req_a.line_ids[1]
        self._delegate(line, self.req_b)
        self.assertEqual(line.requisition_id, self.req_b)

    def test_delegate_target_must_be_open(self):
        self.req_b.action_cancel()
        with self.assertRaises(ValidationError):
            self._delegate(self.req_a.line_ids[1], self.req_b)

    def test_delegate_blocked_with_ordered_quantity(self):
        self.req_a.action_confirm()
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "requisition_id": self.req_a.id,
                "order_line": [
                    (0, 0, {"product_id": self.other_product.id, "product_qty": 5})
                ],
            }
        )
        line = self.req_a.line_ids[1]
        self.assertTrue(line.has_quotation_line)
        order.button_confirm()
        with self.assertRaises(UserError):
            line.button_move_lines_to_different_requisition()

    def test_totals_by_product(self):
        wizard = (
            self.env["grouped.purchase.requisition"]
            .with_context(default_requisition_id=self.req_a.id)
            .create({})
        )
        totals = {total.product_id: total for total in wizard.grouped_line_ids}
        self.assertEqual(len(totals), 2)
        self.assertEqual(totals[self.product].product_qty, 14)
        self.assertEqual(totals[self.product].schedule_date, date(2025, 3, 1))
        self.assertEqual(totals[self.other_product].product_qty, 5)

    def test_has_justificativa(self):
        line = self.req_a.line_ids[0]
        self.assertFalse(line.has_justificativa)
        line.justificativa = "Urgent"
        self.assertTrue(line.has_justificativa)

    def _create_order(self, requisition, product, state=None):
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "requisition_id": requisition.id,
                "order_line": [(0, 0, {"product_id": product.id, "product_qty": 1})],
            }
        )
        if state == "cancel":
            order.button_cancel()
        return order

    def test_can_move_follows_requisition_state(self):
        line = self.req_a.line_ids[0]
        self.assertTrue(line.can_move)
        self.req_a.action_confirm()
        self.assertTrue(line.can_move)
        self.req_a.action_done()
        self.assertFalse(line.can_move)

    def test_move_blocked_when_requisition_is_not_open(self):
        self.req_a.action_cancel()
        line = self.req_a.line_ids[0]
        self.assertFalse(line.can_move)
        with self.assertRaisesRegex(UserError, "draft or confirmed"):
            line.button_move_lines_to_different_requisition()

    def test_move_action_carries_line_and_requisition(self):
        line = self.req_a.line_ids[0]
        action = line.button_move_lines_to_different_requisition()
        self.assertEqual(action["res_model"], "purchase.requisition.delegate")
        self.assertEqual(
            action["context"],
            {
                "default_purchase_requisition_id": self.req_a.id,
                "default_purchase_requisition_line_id": line.id,
            },
        )

    def test_show_justificativa_notification(self):
        line = self.req_a.line_ids[0]
        line.justificativa = "Urgent"
        action = line.action_show_justificativa()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(action["params"]["message"], "Urgent")
        line.justificativa = False
        self.assertEqual(line.action_show_justificativa()["params"]["message"], "")

    def test_requisition_line_quotations(self):
        line = self.req_a.line_ids.filtered(
            lambda ln: ln.product_id == self.other_product
        )
        self.assertFalse(line.has_quotation_line)
        cancelled = self._create_order(self.req_a, self.other_product, "cancel")
        self.assertFalse(line.has_quotation_line)
        order = self._create_order(self.req_a, self.other_product)
        self.assertTrue(line.has_quotation_line)
        action = line.action_view_quotations()
        self.assertEqual(action["res_model"], "purchase.order")
        self.assertEqual(action["domain"], [("id", "in", order.ids)])
        self.assertNotIn(cancelled.id, action["domain"][0][2])

    def test_order_line_sees_quotations_of_siblings(self):
        order = self._create_order(self.req_a, self.product)
        line = order.order_line
        self.assertFalse(line.has_quotation_line)
        self.assertFalse(order._get_sibling_orders())
        sibling = self._create_order(self.req_a, self.product)
        self._create_order(self.req_a, self.other_product, "cancel")
        self.assertEqual(order._get_sibling_orders(), sibling)
        # o valor é recalculado na próxima leitura (a tela relê o registro)
        line.invalidate_recordset(["has_quotation_line"])
        self.assertTrue(line.has_quotation_line)
        action = line.action_view_quotations()
        self.assertEqual(action["domain"], [("id", "in", sibling.ids)])

    def test_display_total_quantities_action(self):
        action = self.req_a.button_display_total_qties()
        self.assertEqual(action["context"], {"default_requisition_id": self.req_a.id})
        self.assertEqual(action["res_model"], "grouped.purchase.requisition")

    def test_wizards_open_for_regular_user(self):
        user = self.env["res.users"].create(
            {
                "name": "Wizard user",
                "login": "wizard_user_access",
                "groups_id": [
                    (6, 0, [self.env.ref("purchase.group_purchase_user").id])
                ],
            }
        )
        for model in (
            "purchase.requisition.delegate",
            "grouped.purchase.requisition",
            "grouped.requisition.line",
        ):
            self.env[model].with_user(user).check_access("create")
