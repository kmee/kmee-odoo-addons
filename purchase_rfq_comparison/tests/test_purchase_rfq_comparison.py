# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io
from datetime import timedelta

import openpyxl

from odoo import fields
from odoo.tests import tagged

from odoo.addons.purchase_rfq_round.tests.common import RfqRoundCommon


@tagged("post_install", "-at_install")
class TestPurchaseRfqComparison(RfqRoundCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.term_now = cls.env.ref("account.account_payment_term_immediate")
        cls.term_30 = cls.env.ref("account.account_payment_term_30days")
        cls.product_a.seller_ids.filtered(
            lambda s: s.partner_id == cls.vendor_1
        ).rfq_approved = True

    def setUp(self):
        super().setUp()
        self.rfq_round = self._make_round(self.vendor_1 | self.vendor_2)
        self.rfq_round.action_create_rfqs()
        self.quote_1 = self._quote(self.rfq_round, self.vendor_1, self.product_a)
        self.quote_2 = self._quote(self.rfq_round, self.vendor_2, self.product_a)
        self.line_a = self.rfq_round.line_ids.filtered(
            lambda r: r.product_id == self.product_a
        )
        date_order = self.quote_1.order_id.date_order
        self.quote_1.write(
            {
                "price_unit": 9.0,
                "rfq_payment_term_id": self.term_now.id,
                "date_planned": date_order + timedelta(days=10),
            }
        )
        self.quote_2.write(
            {
                "price_unit": 9.05,
                "rfq_payment_term_id": self.term_30.id,
                "date_planned": date_order + timedelta(days=10),
            }
        )

    def test_01_approved_vendor_flag(self):
        self.assertTrue(self.quote_1.rfq_vendor_approved)
        self.assertTrue(self.quote_1.rfq_spec_approved)
        self.assertFalse(self.quote_2.rfq_vendor_approved)

    def test_02_present_value(self):
        self.assertEqual(self.quote_1.rfq_payment_days, 0.0)
        self.assertEqual(self.quote_2.rfq_payment_days, 30.0)
        self.assertAlmostEqual(
            self.quote_1.rfq_present_value, self.quote_1.price_total, places=2
        )
        self.assertAlmostEqual(
            self.quote_2.rfq_present_value, self.quote_2.price_total / 1.01, places=2
        )

    def test_03_score_present_value_favours_longer_terms(self):
        self.rfq_round.price_basis = "present_value"
        self.rfq_round.action_award_best_score()
        self.assertEqual(self.line_a.awarded_partner_id, self.vendor_2)
        self.assertAlmostEqual(self.quote_2.rfq_score, 100.0, places=1)
        self.assertLess(self.quote_1.rfq_score, 100.0)

    def test_04_score_subtotal(self):
        self.rfq_round.price_basis = "subtotal"
        self.rfq_round.action_award_best_score()
        self.assertEqual(self.line_a.awarded_partner_id, self.vendor_1)

    def test_05_lead_time_weight(self):
        self.rfq_round.write(
            {"price_basis": "subtotal", "weight_price": 10.0, "weight_delay": 90.0}
        )
        self.quote_1.date_planned = self.quote_1.order_id.date_order + timedelta(
            days=40
        )
        self.rfq_round.action_award_best_score()
        self.assertEqual(self.line_a.awarded_partner_id, self.vendor_2)

    def test_06_require_approved(self):
        self.rfq_round.write({"price_basis": "present_value", "require_approved": True})
        self.rfq_round.action_award_best_score()
        self.assertEqual(self.line_a.awarded_partner_id, self.vendor_1)
        self.assertFalse(self.quote_2.rfq_eligible)
        self.assertEqual(self.quote_2.rfq_score, 0.0)

    def test_07_expired_quote_not_eligible(self):
        self.quote_2.rfq_validity_date = fields.Date.today() - timedelta(days=1)
        self.rfq_round.action_award_best_score()
        self.assertEqual(self.line_a.awarded_partner_id, self.vendor_1)

    def test_08_import_extra_columns(self):
        order_2 = self.quote_2.order_id
        content = self.rfq_round._generate_response_sheet(order_2)
        book = openpyxl.load_workbook(io.BytesIO(content))
        sheet = book.active
        header = [cell.value for cell in sheet[6]]
        self.assertIn("Payment Terms", header)
        col = {name: header.index(name) + 1 for name in header if name}
        for row in range(7, sheet.max_row + 1):
            sheet.cell(row=row, column=col["Unit Price"], value=8.0)
            sheet.cell(row=row, column=col["Payment Terms"], value="30 Days")
            sheet.cell(row=row, column=col["Valid Until"], value="31/12/2099")
            sheet.cell(row=row, column=col["Minimum Qty"], value=500)
            sheet.cell(row=row, column=col["Meets Specification (Y/N)"], value="Sim")
        output = io.BytesIO()
        book.save(output)
        self._import(self.rfq_round, base64.b64encode(output.getvalue()))
        self.assertEqual(self.quote_2.price_unit, 8.0)
        self.assertEqual(self.quote_2.rfq_payment_term_id, self.term_30)
        self.assertEqual(str(self.quote_2.rfq_validity_date), "2099-12-31")
        self.assertEqual(self.quote_2.rfq_min_qty, 500.0)
        self.assertFalse(self.quote_2.rfq_min_qty_ok)
        self.assertTrue(self.quote_2.rfq_spec_approved)
        # Pontuação recalculada na importação.
        self.assertGreater(self.quote_2.rfq_score, 0.0)
        response = self.rfq_round.response_ids.filtered(
            lambda r: r.product_id == self.product_a
        )
        self.assertEqual(response.payment_term_id, self.term_30)
        self.assertTrue(response.spec_approved)

    def test_09_vendor_layout_punctuation_and_cash_term(self):
        """Cabeçalho com pontuação ("Cond. Pgto") e condição "à vista"."""
        file_b64 = self._xlsx(
            [
                ["Cód.", "Valor Unit. (R$)", "Cond. Pgto", "Lote mín."],
                ["ITEM-A", "8,90", "À vista", 50],
            ]
        )
        self.quote_2.rfq_payment_term_id = self.term_30
        self._import(self.rfq_round, file_b64, order=self.quote_2.order_id)
        self.assertEqual(self.quote_2.price_unit, 8.9)
        self.assertEqual(self.quote_2.rfq_payment_term_id, self.term_now)
        self.assertEqual(self.quote_2.rfq_min_qty, 50.0)
