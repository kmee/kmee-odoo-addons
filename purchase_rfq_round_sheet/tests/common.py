# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io

import openpyxl

from odoo.addons.purchase_rfq_round.tests.common import RfqRoundCommon


class RfqRoundSheetCommon(RfqRoundCommon):
    @staticmethod
    def _xlsx(rows):
        book = openpyxl.Workbook()
        sheet = book.active
        for row in rows:
            sheet.append(row)
        output = io.BytesIO()
        book.save(output)
        return base64.b64encode(output.getvalue())

    def _import(self, rfq_round, file_b64, order=None, name="answer.xlsx"):
        wizard = self.env["purchase.rfq.round.import"].create(
            {
                "round_id": rfq_round.id,
                "file": file_b64,
                "file_name": name,
                "order_id": order.id if order else False,
            }
        )
        wizard.action_analyze()
        wizard.action_import()
        return wizard
