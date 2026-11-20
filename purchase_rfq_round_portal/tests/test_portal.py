# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re
from datetime import timedelta

from odoo import Command, fields
from odoo.tests import HttpCase, tagged

from odoo.addons.purchase_rfq_round_portal.models.purchase_order import _parse_float


class RfqRoundPortalCommon(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {"name": "Portal Vendor", "email": "vendor@example.com", "is_company": True}
        )
        cls.other = cls.env["res.partner"].create(
            {"name": "Other Vendor", "email": "other@example.com", "is_company": True}
        )
        cls.product_a = cls.env["product.product"].create(
            {"name": "Portal Item A", "default_code": "PA"}
        )
        cls.product_b = cls.env["product.product"].create(
            {"name": "Portal Item B", "default_code": "PB"}
        )
        cls.rfq_round = cls.env["purchase.rfq.round"].create(
            {
                "date_deadline": fields.Date.today() + timedelta(days=3),
                "vendor_ids": [Command.set((cls.vendor | cls.other).ids)],
                "line_ids": [
                    Command.create({"product_id": cls.product_a.id, "product_qty": 10}),
                    Command.create({"product_id": cls.product_b.id, "product_qty": 5}),
                ],
            }
        )
        cls.rfq_round.action_create_rfqs()
        cls.order = cls.rfq_round.order_ids.filtered(
            lambda o: o.partner_id == cls.vendor
        )
        cls.order._portal_ensure_token()
        cls.line_a = cls.order.order_line.filtered(
            lambda pol: pol.product_id == cls.product_a
        )
        cls.line_b = cls.order.order_line.filtered(
            lambda pol: pol.product_id == cls.product_b
        )

    def _url(self, token=None):
        token = token or self.order.access_token
        return f"/my/purchase/{self.order.id}/rfq_response?access_token={token}"

    def _post(self, data):
        page = self.url_open(self._url())
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        data = dict(data, csrf_token=csrf, access_token=self.order.access_token)
        return self.url_open(f"/my/purchase/{self.order.id}/rfq_response", data=data)


@tagged("post_install", "-at_install")
class TestRfqRoundPortal(RfqRoundPortalCommon):
    def test_01_page_with_token(self):
        response = self.url_open(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("Portal Item A", response.text)
        self.assertIn(f"price_unit_{self.line_a.id}", response.text)

    def test_02_order_page_links_to_answer(self):
        response = self.url_open(self.order.get_portal_url())
        self.assertIn("rfq_response", response.text)

    def test_03_submit_answer(self):
        response = self._post(
            {
                f"price_unit_{self.line_a.id}": "12,50",
                f"delay_{self.line_a.id}": "7",
                f"note_{self.line_a.id}": "laudo por lote",
                f"price_unit_{self.line_b.id}": "",
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("answer was recorded", response.text)
        self.assertEqual(self.line_a.price_unit, 12.5)
        self.assertEqual(self.line_b.price_unit, 0.0)
        lead = (self.line_a.date_planned - self.order.date_order).days
        self.assertEqual(lead, 7)
        responses = self.rfq_round.response_ids
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses.source, "portal")
        self.assertEqual(responses.note, "laudo por lote")
        self.assertEqual(responses.partner_id, self.vendor)
        self.assertIn("through the portal", self.rfq_round.message_ids[0].body)

    def test_04_invalid_value_saves_nothing(self):
        response = self._post(
            {
                f"price_unit_{self.line_a.id}": "abc",
                f"price_unit_{self.line_b.id}": "3",
            }
        )
        self.assertIn("Invalid price", response.text)
        self.assertEqual(self.line_b.price_unit, 0.0)
        self.assertFalse(self.rfq_round.response_ids)

    def test_05_after_deadline_read_only(self):
        self.rfq_round.date_deadline = fields.Date.today() - timedelta(days=1)
        response = self._post({f"price_unit_{self.line_a.id}": "9"})
        self.assertIn("can no longer be answered", response.text)
        self.assertEqual(self.line_a.price_unit, 0.0)

    def test_06_closed_round_read_only(self):
        self.line_a.price_unit = 10.0
        self.rfq_round.action_award_best_price()
        self.rfq_round.action_close()
        response = self.url_open(self._url())
        self.assertIn("can no longer be answered", response.text)
        self.assertNotIn("Send answer", response.text)

    def test_07_wrong_token(self):
        response = self.url_open(self._url(token="wrong"))
        self.assertNotIn("Portal Item A", response.text)

    def test_08_formatted_values_round_trip(self):
        """Valor gravado volta formatado e é lido de novo sem perda."""
        self.line_a.price_unit = 1234.5
        page = self.url_open(self._url())
        match = re.search(
            rf'name="price_unit_{self.line_a.id}" value="([^"]+)"', page.text
        )
        shown = match.group(1)
        self._post({f"price_unit_{self.line_a.id}": shown})
        self.assertEqual(self.line_a.price_unit, 1234.5)

    def test_09_parse_float(self):
        cases = [
            ("1.234,50", ",", 1234.5),
            ("1,234.50", ".", 1234.5),
            ("12,50", ",", 12.5),
            ("12,50", ".", 12.5),
            ("48.3", ",", 48.3),
            ("1,234", ".", 1234.0),
            ("1.234.567", ",", 1234567.0),
            ("R$ 9,90", ",", 9.9),
        ]
        for raw, decimal_point, expected in cases:
            self.assertEqual(_parse_float(raw, decimal_point), expected, raw)
        self.assertIsNone(_parse_float("  ", ","))
