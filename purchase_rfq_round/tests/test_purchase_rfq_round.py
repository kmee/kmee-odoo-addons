# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.queue_job.tests.common import trap_jobs

from .common import RfqRoundCommon


@tagged("post_install", "-at_install")
class TestPurchaseRfqRound(RfqRoundCommon):
    def test_01_round_from_request_lines(self):
        rfq_round = self._make_round()
        self.assertEqual(rfq_round.state, "draft")
        self.assertEqual(len(rfq_round.line_ids), 2)
        line_a = rfq_round.line_ids.filtered(lambda r: r.product_id == self.product_a)
        self.assertEqual(line_a.product_qty, 100.0)
        self.assertEqual(line_a.request_line_ids.product_id, self.product_a)
        # Fornecedores sugeridos pelos cadastros dos produtos.
        self.assertEqual(
            rfq_round.vendor_ids, self.vendor_1 | self.vendor_2 | self.vendor_3
        )
        # Sem compra anterior, a referência vem do menor preço da tabela.
        self.assertEqual(line_a.reference_price, 10.0)
        self.assertEqual(line_a.reference_source, "vendor_price")
        self.assertEqual(self.request.line_ids.rfq_round_id, rfq_round)

    def test_02_lines_already_in_round_rejected(self):
        self._make_round()
        with self.assertRaises(UserError):
            self._make_round()

    def test_03_create_rfqs_in_one_group(self):
        rfq_round = self._make_round()
        rfq_round.action_create_rfqs()
        self.assertEqual(rfq_round.state, "quoting")
        self.assertEqual(len(rfq_round.order_ids), 3)
        self.assertEqual(len(rfq_round.order_ids.purchase_group_id), 1)
        self.assertEqual(rfq_round.order_ids[0].alternative_po_ids, rfq_round.order_ids)
        for order in rfq_round.order_ids:
            self.assertEqual(len(order.order_line), 2)
            self.assertFalse(any(order.order_line.mapped("price_unit")))
        self.assertEqual(len(rfq_round.line_ids.quote_line_ids), 6)

    def test_04_send_without_sheet(self):
        rfq_round = self._make_round()
        rfq_round.action_create_rfqs()
        rfq_round.action_send_rfqs()
        self.assertEqual(set(rfq_round.order_ids.mapped("state")), {"sent"})
        # Fornecedor sem e-mail: aviso no chatter da cotação.
        order_3 = rfq_round.order_ids.filtered(lambda o: o.partner_id == self.vendor_3)
        self.assertIn("another channel", order_3.message_ids[0].body)

    def test_04b_snapshot_responses(self):
        rfq_round = self._make_round()
        rfq_round.action_create_rfqs()
        self._answer(rfq_round)
        rfq_round.action_award_best_price()
        rfq_round.action_close()
        # 5 respostas com preço (vendor_3 não respondeu o item A).
        self.assertEqual(len(rfq_round.response_ids), 5)
        self.assertEqual(set(rfq_round.response_ids.mapped("source")), {"manual"})
        rfq_round.action_close()
        self.assertEqual(len(rfq_round.response_ids), 5)

    def _answer(self, rfq_round):
        prices = {
            (self.vendor_1, self.product_a): 9.0,
            (self.vendor_2, self.product_a): 9.5,
            (self.vendor_3, self.product_a): 0.0,
            (self.vendor_1, self.product_b): 22.0,
            (self.vendor_2, self.product_b): 18.0,
            (self.vendor_3, self.product_b): 18.5,
        }
        for (vendor, product), price in prices.items():
            self._quote(rfq_round, vendor, product).price_unit = price

    def test_05_award_best_price_and_close(self):
        rfq_round = self._make_round()
        rfq_round.action_create_rfqs()
        self._answer(rfq_round)
        rfq_round.action_award_best_price()
        line_a = rfq_round.line_ids.filtered(lambda r: r.product_id == self.product_a)
        line_b = rfq_round.line_ids.filtered(lambda r: r.product_id == self.product_b)
        self.assertEqual(line_a.awarded_partner_id, self.vendor_1)
        self.assertEqual(line_b.awarded_partner_id, self.vendor_2)
        # Saving sobre a referência (10 e 19): (10 - 9) * 100 + (19 - 18) * 50
        self.assertAlmostEqual(rfq_round.amount_saving, 150.0)
        rfq_round.action_close()
        self.assertEqual(rfq_round.state, "done")
        order_1 = rfq_round.order_ids.filtered(lambda o: o.partner_id == self.vendor_1)
        order_2 = rfq_round.order_ids.filtered(lambda o: o.partner_id == self.vendor_2)
        order_3 = rfq_round.order_ids.filtered(lambda o: o.partner_id == self.vendor_3)
        self.assertEqual(order_3.state, "cancel")
        self.assertEqual(order_1.order_line.product_id, self.product_a)
        self.assertEqual(order_2.order_line.product_id, self.product_b)
        # Vencedoras continuam cotação: seguem a aprovação normal.
        self.assertIn(order_1.state, ("draft", "sent"))
        # Requisição ligada só às vencedoras (lacuna 3).
        req_a = self.request.line_ids.filtered(lambda r: r.product_id == self.product_a)
        self.assertEqual(req_a.purchase_lines, order_1.order_line)
        self.assertEqual(req_a.purchased_qty, 100.0)
        self.assertEqual(self.request.state, "in_progress")
        # Idempotente.
        rfq_round.action_close()
        self.assertEqual(len(req_a.purchase_lines), 1)
        self.assertEqual(
            len(
                self.env["purchase.request.allocation"].search(
                    [("purchase_request_line_id", "=", req_a.id)]
                )
            ),
            1,
        )

    def test_06_manual_award_and_best_date(self):
        rfq_round = self._make_round()
        rfq_round.action_create_rfqs()
        self._answer(rfq_round)
        quote = self._quote(rfq_round, self.vendor_2, self.product_a)
        quote.action_rfq_round_award()
        self.assertTrue(quote.rfq_round_awarded)
        with self.assertRaises(UserError):
            self._quote(
                rfq_round, self.vendor_3, self.product_a
            ).action_rfq_round_award()
        rfq_round.action_award_best_date()
        self.assertTrue(all(rfq_round.line_ids.mapped("awarded_po_line_id")))

    def test_07_close_requires_award(self):
        rfq_round = self._make_round()
        rfq_round.action_create_rfqs()
        with self.assertRaises(UserError):
            rfq_round.action_close()

    def test_08_new_round_uses_best_price_as_reference(self):
        rfq_round = self._make_round()
        rfq_round.action_create_rfqs()
        self._answer(rfq_round)
        action = rfq_round.action_new_round()
        new_round = self.env["purchase.rfq.round"].browse(action["res_id"])
        self.assertEqual(rfq_round.state, "replaced")
        self.assertEqual(set(rfq_round.order_ids.mapped("state")), {"cancel"})
        self.assertEqual(new_round.parent_id, rfq_round)
        self.assertEqual(new_round.round_number, 2)
        line_a = new_round.line_ids.filtered(lambda r: r.product_id == self.product_a)
        self.assertEqual(line_a.reference_price, 9.0)
        self.assertEqual(line_a.reference_source, "previous_round")
        self.assertEqual(line_a.request_line_ids.product_id, self.product_a)
        # Requisições continuam numa rodada ativa: a nova.
        self.assertEqual(self.request.line_ids.rfq_round_id, new_round)
        new_round.action_create_rfqs()
        self.assertEqual(len(new_round.order_ids), 3)

    def test_09_reference_from_last_purchase(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor_1.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 1,
                            "price_unit": 8.5,
                        },
                    )
                ],
            }
        )
        po.button_confirm()
        rfq_round = self._make_round()
        line_a = rfq_round.line_ids.filtered(lambda r: r.product_id == self.product_a)
        self.assertEqual(line_a.reference_price, 8.5)
        self.assertEqual(line_a.reference_source, "last_purchase")

    def test_10_large_round_uses_jobs(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "purchase_rfq_round.job_threshold", 1
        )
        rfq_round = self._make_round()
        with trap_jobs() as trap:
            rfq_round.action_create_rfqs()
            trap.assert_jobs_count(2)
            self.assertEqual(len(rfq_round.order_ids), 1)
            trap.perform_enqueued_jobs()
        self.assertEqual(len(rfq_round.order_ids), 3)
        self.assertEqual(len(rfq_round.order_ids.purchase_group_id), 1)

    def test_11_cancel_and_reset(self):
        rfq_round = self._make_round()
        rfq_round.action_create_rfqs()
        rfq_round.action_cancel()
        self.assertEqual(set(rfq_round.order_ids.mapped("state")), {"cancel"})
        self.assertFalse(self.request.line_ids.rfq_round_id)
        rfq_round.action_draft()
        self.assertEqual(rfq_round.state, "draft")

    def test_12_compare_action(self):
        rfq_round = self._make_round()
        rfq_round.action_create_rfqs()
        action = rfq_round.action_compare()
        lines = self.env["purchase.order.line"].search(action["domain"])
        self.assertEqual(len(lines), 6)

    def test_13_award_wizard(self):
        rfq_round = self._make_round()
        rfq_round.action_create_rfqs()
        self.assertTrue(rfq_round.has_unsent_orders)
        rfq_round.action_send_rfqs()
        self.assertFalse(rfq_round.has_unsent_orders)
        self._answer(rfq_round)
        # Escolha manual do item A fica; o item B vai pelo critério.
        manual = self._quote(rfq_round, self.vendor_2, self.product_a)
        manual.action_rfq_round_award()
        action = rfq_round.action_open_award()
        wizard = (
            self.env[action["res_model"]]
            .with_context(**action["context"])
            .create({"criterion": "price"})
        )
        self.assertTrue(wizard.only_unawarded)
        wizard.action_apply()
        line_a = rfq_round.line_ids.filtered(lambda r: r.product_id == self.product_a)
        line_b = rfq_round.line_ids.filtered(lambda r: r.product_id == self.product_b)
        self.assertEqual(line_a.awarded_po_line_id, manual)
        self.assertEqual(line_b.awarded_partner_id, self.vendor_2)
        # Sem manter as escolhas, o item A vai para o melhor preço.
        wizard.write({"only_unawarded": False})
        wizard.action_apply()
        self.assertEqual(line_a.awarded_partner_id, self.vendor_1)
