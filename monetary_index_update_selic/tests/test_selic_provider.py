from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@tagged("post_install", "-at_install")
class TestSelicProvider(TransactionCase):
    def setUp(self):
        super().setUp()
        self.provider = self.env["monetary.index.provider"]
        self.index = self.env.ref("monetary_index_update_selic.monetary_index_selic")

    @patch(
        "odoo.addons.monetary_index_update_selic.models.monetary_index_provider.requests.get"
    )
    def test_update_selic_rates_creates_rates(self, mock_get):
        payload = [
            {"data": "02/01/2025", "valor": "0.043225"},
            {"data": "03/01/2025", "valor": "0.043225"},
        ]
        mock_get.return_value = DummyResponse(payload)

        result = self.provider.update_selic_rates()

        self.assertEqual(result["created"], 2)
        rates = self.env["monetary.index.rate"].search(
            [("index_id", "=", self.index.id)]
        )
        self.assertEqual(len(rates), 2)

    @patch(
        "odoo.addons.monetary_index_update_selic.models.monetary_index_provider.requests.get"
    )
    def test_update_selic_rates_updates_existing(self, mock_get):
        rate = self.env["monetary.index.rate"].create(
            {
                "index_id": self.index.id,
                "date": "2025-01-02",
                "value": 0.1,
                "source": "manual",
            }
        )
        payload = [{"data": "02/01/2025", "valor": "0.043225"}]
        mock_get.return_value = DummyResponse(payload)

        result = self.provider.update_selic_rates()

        self.assertEqual(result["updated"], 1)
        self.assertEqual(rate.value, 0.043225)
