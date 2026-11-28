# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestMrpPurchaseRequisition(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.production = cls.env.ref("mrp_purchase_requisition.mrp_production_painel")
        cls.cable = cls.env.ref("mrp_purchase_requisition.product_chicote")

    def _wizard(self):
        wizard_model = self.env["mrp.production.purchase.requisition"].with_context(
            default_production_id=self.production.id
        )
        return wizard_model.create(wizard_model.default_get(list(wizard_model._fields)))

    def test_requisition_from_missing_components(self):
        wizard = self._wizard()
        self.assertTrue(wizard.is_first_requisition)
        self.assertEqual(
            wizard.line_ids.product_id, self.production.move_raw_ids.product_id
        )
        cable_line = wizard.line_ids.filtered(
            lambda line: line.product_id == self.cable
        )
        self.assertEqual(cable_line.product_qty, 20.0)
        action = wizard.create_purchase_requisition()
        requisition = self.env["purchase.requisition"].browse(action["res_id"])
        self.assertEqual(requisition.line_ids.production_id, self.production)
        self.assertEqual(requisition.production_origins, self.production.display_name)
        self.assertEqual(
            requisition.procurement_group_id, self.production.procurement_group_id
        )
        self.production.invalidate_recordset()
        self.assertEqual(self.production.requisition_count, 1)
        self.assertEqual(self.production.requisition_line_count, 2)

    def test_second_requisition_needs_justification(self):
        self._wizard().create_purchase_requisition()
        self.production.invalidate_recordset()
        wizard = self._wizard()
        self.assertFalse(wizard.is_first_requisition)
        with self.assertRaises(UserError):
            wizard.create_purchase_requisition()
        wizard.justificativa = "Quantidade adicional para perdas"
        wizard.create_purchase_requisition()
        self.production.invalidate_recordset()
        self.assertEqual(self.production.requisition_count, 2)

    def test_component_in_other_uom_of_same_category(self):
        dozen = self.env.ref("uom.product_uom_dozen")
        move = self.production.move_raw_ids.filtered(
            lambda move: move.product_id == self.cable
        )
        move.product_uom = dozen
        wizard = self._wizard()
        line = wizard.line_ids.filtered(lambda line: line.product_id == self.cable)
        self.assertEqual(line.product_uom_id, dozen)
        action = wizard.create_purchase_requisition()
        requisition = self.env["purchase.requisition"].browse(action["res_id"])
        req_line = requisition.line_ids.filtered(lambda rl: rl.product_id == self.cable)
        self.assertEqual(req_line.product_uom_id, dozen)
        order_form = Form(self.env["purchase.order"])
        order_form.partner_id = self.env.ref("base.res_partner_12")
        order = order_form.save()
        order.requisition_id = requisition
        order._onchange_requisition_id()
        po_line = order.order_line.filtered(lambda pol: pol.product_id == self.cable)
        self.assertTrue(po_line)
        order.button_confirm()
        req_line.invalidate_recordset()
        self.assertEqual(req_line.qty_ordered, req_line.product_qty)

    def test_button_opens_wizard_for_production(self):
        action = self.production.button_create_purchase_requisition()
        self.assertEqual(action["res_model"], "mrp.production.purchase.requisition")
        self.assertEqual(
            action["context"], {"default_production_id": self.production.id}
        )

    def test_nothing_to_request(self):
        wizard = self._wizard()
        wizard.line_ids.product_qty = 0
        with self.assertRaisesRegex(UserError, "no quantity"):
            wizard.create_purchase_requisition()

    def test_line_below_missing_quantity(self):
        wizard = self._wizard()
        line = wizard.line_ids[0]
        self.assertFalse(line.below_missing)
        line.product_qty = line.missing_qty - 1
        self.assertTrue(line.below_missing)
        line.product_qty = line.missing_qty + 1
        self.assertFalse(line.below_missing)

    def test_smart_buttons_list_requisition_records(self):
        self.assertFalse(self.production.action_view_requisitions()["domain"][0][2])
        action = self._wizard().create_purchase_requisition()
        requisition = self.env["purchase.requisition"].browse(action["res_id"])
        self.production.invalidate_recordset()
        self.assertEqual(
            self.production.action_view_requisition_lines()["domain"],
            [("id", "in", requisition.line_ids.ids)],
        )
        self.assertEqual(
            self.production.action_view_requisitions()["domain"],
            [("id", "in", requisition.ids)],
        )
        self.assertEqual(self.production.action_view_requisitions()["context"], {})
        # sem pedido confirmado, ainda não há pedidos nem recebimentos
        self.assertFalse(self.production.purchase_count)
        self.assertFalse(self.production.purchase_move_count)

    def test_smart_buttons_list_purchase_orders_and_moves(self):
        action = self._wizard().create_purchase_requisition()
        requisition = self.env["purchase.requisition"].browse(action["res_id"])
        requisition.action_confirm()
        order_form = Form(self.env["purchase.order"])
        order_form.partner_id = self.env.ref("base.res_partner_12")
        order = order_form.save()
        order.requisition_id = requisition
        order._onchange_requisition_id()
        order.button_confirm()
        self.production.invalidate_recordset()
        self.assertEqual(self.production.purchase_ids, order)
        self.assertEqual(self.production.purchase_count, 1)
        moves = order.picking_ids.move_ids.filtered(
            lambda move: move.product_id in self.production.move_raw_ids.product_id
        )
        self.assertTrue(moves)
        self.assertEqual(self.production.purchase_move_ids, moves)
        self.assertEqual(self.production.purchase_move_count, len(moves))
        moves_action = self.production.action_view_purchase_moves()
        self.assertEqual(moves_action["domain"], [("id", "in", moves.ids)])

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
            "mrp.production.purchase.requisition",
            "mrp.production.purchase.requisition.line",
        ):
            self.env[model].with_user(user).check_access("create")
