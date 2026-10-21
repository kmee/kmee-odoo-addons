# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInstallments(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["payment.provider"].create(
            {"name": "Installment Provider", "code": "none"}
        )
        cls.term = cls.env["account.payment.term"].create(
            {
                "name": "3x",
                "is_installment": True,
                "provider_id": cls.provider.id,
                "installment_rate": 2.0,
                "installment_type": "simple",
                "line_ids": [
                    (0, 0, {"value": "percent", "value_amount": 33.33, "nb_days": 30}),
                    (0, 0, {"value": "percent", "value_amount": 33.33, "nb_days": 60}),
                    (0, 0, {"value": "percent", "value_amount": 33.34, "nb_days": 90}),
                ],
            }
        )

    def test_compute_options_simple_interest(self):
        options = self.term.compute_installment_options(300.0)
        self.assertEqual(options, ["3x de R$ 104.00 com juros"])

    def test_compute_options_compound_interest(self):
        self.term.installment_type = "compose"
        options = self.term.compute_installment_options(300.0)
        self.assertEqual(len(options), 1)
        self.assertIn("com juros", options[0])

    def test_compute_options_without_interest(self):
        self.term.installment_rate = 0.0
        self.assertEqual(
            self.term.compute_installment_options(300.0),
            ["3x de R$ 100.00 sem juros"],
        )

    def test_not_installment_returns_single_option(self):
        self.term.is_installment = False
        self.assertEqual(
            self.term.compute_installment_options(50.0), ["1x de R$ 50.00"]
        )

    def test_provider_options(self):
        options = self.provider.get_installment_options(300.0)
        self.assertEqual(options[0]["value"], "1")
        self.assertEqual(options[1]["value"], "3")
        self.assertEqual(len(options), 2)
