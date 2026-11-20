# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from .common import RfqRoundSheetCommon


@tagged("post_install", "-at_install")
class TestPurchaseRfqRoundSend(RfqRoundSheetCommon):
    def test_01_send_attaches_sheet(self):
        rfq_round = self._make_round()
        rfq_round.action_create_rfqs()
        rfq_round.action_send_rfqs()
        self.assertEqual(set(rfq_round.order_ids.mapped("state")), {"sent"})
        attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "purchase.order"),
                ("res_id", "in", rfq_round.order_ids.ids),
                ("name", "=like", "%.xlsx"),
            ]
        )
        self.assertEqual(len(attachments), 3)

    def test_02_import_action(self):
        rfq_round = self._make_round()
        action = rfq_round.action_import_responses()
        self.assertEqual(action["res_model"], "purchase.rfq.round.import")
        self.assertEqual(action["context"]["default_round_id"], rfq_round.id)
