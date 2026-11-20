# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from .common import DdmrpPurchaseRequestCommon


@tagged("post_install", "-at_install")
class TestDdmrpPurchaseRequest(DdmrpPurchaseRequestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls._create_product("Requested item")
        cls.buffer = cls._create_buffer(cls.product)

    def _request_lines(self):
        return self.env["purchase.request.line"].search(
            [("product_id", "=", self.product.id)]
        )

    def test_01_request_line_linked_to_buffer(self):
        recommended = self.buffer.procure_recommended_qty
        self.assertGreater(recommended, 0.0)
        self._procure(self.buffer)
        line = self._request_lines()
        self.assertEqual(len(line), 1)
        self.assertEqual(line.buffer_id, self.buffer)
        self.assertEqual(line.product_qty, recommended)
        self.assertEqual(line.buffer_pending_qty, recommended)
        self.assertEqual(self.buffer.purchase_request_pending_qty, recommended)
        self.assertEqual(self.buffer.purchase_request_count, 1)

    def test_02_open_request_reduces_recommendation(self):
        """Lacuna 1: a requisição aberta não pode ser recomendada de novo."""
        self._procure(self.buffer)
        self.assertEqual(self.buffer.procure_recommended_qty, 0.0)

    def test_03_converted_request_counted_once(self):
        recommended = self.buffer.procure_recommended_qty
        self._procure(self.buffer)
        line = self._request_lines()
        line.request_id.button_to_approve()
        line.request_id.button_approved()
        wizard = (
            self.env["purchase.request.line.make.purchase.order"]
            .with_context(active_model="purchase.request.line", active_ids=line.ids)
            .create({"supplier_id": self.vendor_a.id})
        )
        wizard.make_purchase_order()
        self.buffer.invalidate_recordset()
        self.buffer.cron_actions()
        self.assertEqual(line.buffer_pending_qty, 0.0)
        # A quantidade está agora na RFQ, contada uma vez só.
        self.assertEqual(self.buffer.rfq_total_qty, recommended)
        self.assertEqual(
            self.buffer._quantity_in_progress()[self.buffer.id], recommended
        )
        self.assertEqual(self.buffer.procure_recommended_qty, 0.0)

    def test_04_rejected_request_released(self):
        recommended = self.buffer.procure_recommended_qty
        self._procure(self.buffer)
        line = self._request_lines()
        line.request_id.button_rejected()
        self.buffer.invalidate_recordset()
        self.buffer.cron_actions()
        self.assertEqual(line.buffer_pending_qty, 0.0)
        self.assertEqual(self.buffer.procure_recommended_qty, recommended)

    def test_05_without_flag_keeps_rfq_flow(self):
        product = self._create_product("Plain item", purchase_request=False)
        buffer = self._create_buffer(product)
        self._procure(buffer, partner=self.vendor_b)
        self.assertFalse(buffer.purchase_request_line_ids)
        self.assertEqual(buffer.purchase_line_ids.order_id.partner_id, self.vendor_b)

    def test_06_action_view_purchase_request(self):
        self._procure(self.buffer)
        action = self.buffer.action_view_purchase_request()
        self.assertEqual(action["domain"], [("buffer_id", "=", self.buffer.id)])
