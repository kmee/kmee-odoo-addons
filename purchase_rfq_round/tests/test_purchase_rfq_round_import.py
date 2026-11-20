# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io

import openpyxl

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import RfqRoundCommon


@tagged("post_install", "-at_install")
class TestPurchaseRfqRoundImport(RfqRoundCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rfq_round = cls._make_round_cls()
        cls.rfq_round.action_create_rfqs()
        cls.order_1 = cls.rfq_round.order_ids.filtered(
            lambda o: o.partner_id == cls.vendor_1
        )

    @classmethod
    def _make_round_cls(cls):
        wizard = (
            cls.env["purchase.request.line.make.rfq.round"]
            .with_context(
                active_model="purchase.request.line",
                active_ids=cls.request.line_ids.ids,
            )
            .create({})
        )
        return cls.env["purchase.rfq.round"].browse(wizard.action_create()["res_id"])

    def test_01_roundtrip_standard_sheet(self):
        """A planilha gerada pela rodada volta preenchida e é importada."""
        content = self.rfq_round._generate_response_sheet(self.order_1)
        book = openpyxl.load_workbook(io.BytesIO(content))
        sheet = book.active
        header = [cell.value for cell in sheet[6]]
        price_col = header.index("Unit Price") + 1
        delay_col = price_col + 1
        for row in range(7, sheet.max_row + 1):
            sheet.cell(row=row, column=price_col, value="9,75")
            sheet.cell(row=row, column=delay_col, value=15)
        output = io.BytesIO()
        book.save(output)
        wizard = self._import(
            self.rfq_round, base64.b64encode(output.getvalue()), name="one.xlsx"
        )
        self.assertIn("2 items imported", wizard.result)
        self.assertEqual(set(self.order_1.order_line.mapped("price_unit")), {9.75})
        responses = self.rfq_round.response_ids
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses.partner_id, self.vendor_1)
        self.assertEqual(set(responses.mapped("delay")), {15})
        self.assertEqual(responses[0].raw_values["price_unit"], "9,75")
        lead = (self.order_1.order_line[0].date_planned - self.order_1.date_order).days
        self.assertEqual(lead, 15)

    def test_02_vendor_own_layout(self):
        """Planilha do fornecedor, sem ID, outro layout: casa pelo código."""
        file_b64 = self._xlsx(
            [
                ["Proposta comercial"],
                [],
                ["Cód.", "Descrição", "Valor Unitário (R$)", "Prazo (dias)", "Obs"],
                ["ITEM-B", "Item B", "R$ 1.234,50", 20, "frete CIF"],
                ["ITEM-A", "Item A", 8.4, 10, None],
                ["XYZ", "Desconhecido", 5, 1, None],
            ]
        )
        wizard = self._import(self.rfq_round, file_b64, order=self.order_1)
        self.assertEqual(wizard.header_row, 3)
        quote_a = self._quote(self.rfq_round, self.vendor_1, self.product_a)
        quote_b = self._quote(self.rfq_round, self.vendor_1, self.product_b)
        self.assertEqual(quote_a.price_unit, 8.4)
        self.assertEqual(quote_b.price_unit, 1234.5)
        self.assertIn("row 6", wizard.result)
        note = self.rfq_round.response_ids.filtered(
            lambda r: r.product_id == self.product_b
        ).note
        self.assertEqual(note, "frete CIF")

    def test_03_own_layout_requires_order(self):
        file_b64 = self._xlsx([["Código", "Preço"], ["ITEM-A", 10]])
        wizard = self.env["purchase.rfq.round.import"].create(
            {"round_id": self.rfq_round.id, "file": file_b64, "file_name": "x.xlsx"}
        )
        wizard.action_analyze()
        with self.assertRaises(UserError):
            wizard.action_import()

    def test_04_manual_mapping(self):
        file_b64 = self._xlsx(
            [["SKU interno", "Coluna X", "Coluna Y"], ["ITEM-A", "zzz", 7.5]]
        )
        wizard = self.env["purchase.rfq.round.import"].create(
            {
                "round_id": self.rfq_round.id,
                "file": file_b64,
                "file_name": "y.xlsx",
                "order_id": self.order_1.id,
            }
        )
        wizard.action_analyze()
        wizard.column_ids.filtered(lambda c: c.key == "price_unit").column = "C"
        wizard.column_ids.filtered(lambda c: c.key == "default_code").column = "A"
        wizard.header_row = 1
        wizard.action_import()
        quote_a = self._quote(self.rfq_round, self.vendor_1, self.product_a)
        self.assertEqual(quote_a.price_unit, 7.5)

    def test_05_unreadable_file(self):
        wizard = self.env["purchase.rfq.round.import"].create(
            {
                "round_id": self.rfq_round.id,
                "file": base64.b64encode(b"not a spreadsheet"),
                "file_name": "bad.xlsx",
            }
        )
        with self.assertRaises(UserError):
            wizard.action_analyze()
