from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

REQUESTS_GET = (
    "odoo.addons.monetary_index_update_bacen.models.monetary_index_provider."
    "requests.get"
)


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@tagged("post_install", "-at_install")
class TestBacenProvider(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["monetary.index.provider"]
        cls.selic = cls.env.ref("monetary_index_update_bacen.monetary_index_selic")
        cls.ipca = cls.env.ref("monetary_index_update_bacen.monetary_index_ipca")

    def _rates(self, index):
        return self.env["monetary.index.rate"].search([("index_id", "=", index.id)])

    @patch(REQUESTS_GET)
    def test_update_selic_rates_creates_rates(self, mock_get):
        payload = [
            {"data": "02/01/2025", "valor": "0.043225"},
            {"data": "03/01/2025", "valor": "0.043225"},
        ]
        mock_get.return_value = DummyResponse(payload)

        result = self.provider.update_selic_rates()

        self.assertEqual(result["created"], 2)
        self.assertEqual(len(self._rates(self.selic)), 2)
        self.assertIn("bcdata.sgs.4390", mock_get.call_args.args[0])

    @patch(REQUESTS_GET)
    def test_update_selic_rates_updates_existing(self, mock_get):
        rate = self.env["monetary.index.rate"].create(
            {
                "index_id": self.selic.id,
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

    @patch(REQUESTS_GET)
    def test_update_ipca_uses_its_series(self, mock_get):
        payload = [
            {"data": "01/09/2026", "valor": "0,48"},
            {"data": "01/10/2026", "valor": "0.09"},
        ]
        mock_get.return_value = DummyResponse(payload)

        result = self.provider.update_rates(self.ipca)

        self.assertEqual(result["created"], 2)
        self.assertIn("bcdata.sgs.433/", mock_get.call_args.args[0])
        values = sorted(self._rates(self.ipca).mapped("value"))
        self.assertEqual(values, [0.09, 0.48])

    def test_update_without_sgs_code(self):
        index = self.env["monetary.index"].create({"name": "Sem série", "code": "X1"})
        with self.assertRaises(UserError):
            self.provider.update_rates(index)

    @patch(REQUESTS_GET)
    def test_cron_updates_every_index_with_sgs_code(self, mock_get):
        mock_get.return_value = DummyResponse([{"data": "01/10/2026", "valor": "0.1"}])

        result = self.provider.cron_update_rates()

        for code in ("SELIC", "IPCA", "INPC", "IGPM"):
            self.assertIn(code, result)
        self.assertEqual(len(self._rates(self.ipca)), 1)

    @patch(REQUESTS_GET)
    def test_wizard_updates_the_selected_index(self, mock_get):
        mock_get.return_value = DummyResponse([{"data": "01/10/2026", "valor": "0.1"}])
        wizard = (
            self.env["monetary.index.bacen.update.wizard"]
            .with_context(active_model="monetary.index", active_id=self.ipca.id)
            .create({})
        )
        self.assertEqual(wizard.index_id, self.ipca)

        action = wizard.action_update()

        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(len(self._rates(self.ipca)), 1)
