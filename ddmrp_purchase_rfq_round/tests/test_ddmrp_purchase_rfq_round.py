# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.ddmrp_purchase_request.tests.common import DdmrpPurchaseRequestCommon


@tagged("post_install", "-at_install")
class TestDdmrpPurchaseRfqRound(DdmrpPurchaseRequestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor_c = cls.env["res.partner"].create(
            {"name": "Vendor C", "is_company": True}
        )
        cls.product = cls._create_product("Round item")
        cls.buffer = cls._create_buffer(cls.product)

    def _refresh(self, buffer=None):
        # O buffer é atualizado em outra transação (cron ou botão): sem cache.
        self.env.invalidate_all()
        (buffer or self.buffer).cron_actions()

    def _in_progress(self):
        return self.buffer._quantity_in_progress()[self.buffer.id]

    def _approved_request_line(self):
        self._procure(self.buffer)
        line = self.buffer.purchase_request_line_ids
        line.request_id.button_to_approve()
        line.request_id.button_approved()
        return line

    def _round(self, request_line):
        wizard = (
            self.env["purchase.request.line.make.rfq.round"]
            .with_context(
                active_model="purchase.request.line", active_ids=request_line.ids
            )
            .create(
                {
                    "vendor_ids": [
                        (6, 0, (self.vendor_a | self.vendor_b | self.vendor_c).ids)
                    ]
                }
            )
        )
        return self.env["purchase.rfq.round"].browse(wizard.action_create()["res_id"])

    def test_01_round_counted_once(self):
        recommended = self.buffer.procure_recommended_qty
        request_line = self._approved_request_line()
        rfq_round = self._round(request_line)
        # Rodada em rascunho: ainda conta a requisição.
        self._refresh()
        self.assertEqual(self._in_progress(), recommended)
        rfq_round.action_create_rfqs()
        self._refresh()
        self.assertEqual(len(self.buffer.purchase_line_ids), 3)
        # Três cotações da mesma quantidade, contadas uma vez, e a requisição
        # em cotação não entra de novo.
        self.assertEqual(self._in_progress(), recommended)
        self.assertEqual(self.buffer.rfq_total_qty, recommended)
        self.assertEqual(self.buffer.purchase_request_pending_qty, 0.0)
        self.assertEqual(self.buffer.procure_recommended_qty, 0.0)

    def test_02_after_close_only_winner(self):
        recommended = self.buffer.procure_recommended_qty
        request_line = self._approved_request_line()
        rfq_round = self._round(request_line)
        rfq_round.action_create_rfqs()
        for price, order in zip((12.0, 9.0, 10.0), rfq_round.order_ids, strict=True):
            order.order_line.price_unit = price
        rfq_round.action_award_best_price()
        self._refresh()
        self.assertEqual(self._in_progress(), recommended)
        rfq_round.action_close()
        self._refresh()
        self.assertEqual(self._in_progress(), recommended)
        self.assertEqual(request_line.buffer_pending_qty, 0.0)
        winner = rfq_round.line_ids.awarded_po_line_id.order_id
        winner.button_confirm()
        self._refresh()
        # Confirmado, sai do "em andamento" e vira recebimento previsto. Se o
        # vencedor entrega fora da janela do DLT, o ddmrp não conta esse
        # recebimento na posição líquida e volta a recomendar (ver M3).
        self.assertEqual(self._in_progress(), 0.0)
        self.assertEqual(self.buffer.incoming_total_qty, recommended)

    def test_03_plain_alternatives_counted_once(self):
        product = self._create_product("Alternative item", purchase_request=False)
        buffer = self._create_buffer(product)
        recommended = buffer.procure_recommended_qty
        self._procure(buffer)
        order = buffer.purchase_line_ids.order_id
        for vendor in (self.vendor_b, self.vendor_c):
            self.env["purchase.requisition.create.alternative"].create(
                {
                    "origin_po_id": order.id,
                    "partner_id": vendor.id,
                    "copy_products": True,
                }
            ).action_create_alternative()
        self._refresh(buffer)
        self.assertEqual(len(buffer.purchase_line_ids), 3)
        self.assertEqual(buffer.rfq_total_qty, recommended)
        self.assertEqual(buffer._quantity_in_progress()[buffer.id], recommended)
