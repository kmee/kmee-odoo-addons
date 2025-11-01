from odoo.tests.common import SavepointCase


class TestPeriodCommission(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.commission_model = cls.env["sale.commission"]

        cls.period_commission = cls.commission_model.create(
            {
                "name": "Period Commission Test",
                "commission_type": "period_section",
                "invoice_state": "open",
                "amount_base_type": "gross_amount",
                "section_ids": [
                    (0, 0, {"amount_from": 0.0, "amount_to": 100000.0, "percent": 1.0}),
                    (
                        0,
                        0,
                        {
                            "amount_from": 100000.0,
                            "amount_to": 200000.0,
                            "percent": 2.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "amount_from": 200000.0,
                            "amount_to": 300000.0,
                            "percent": 3.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "amount_from": 300000.0,
                            "amount_to": 400000.0,
                            "percent": 4.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "amount_from": 400000.0,
                            "amount_to": 99999999,
                            "percent": 5.0,
                        },
                    ),
                ],
            }
        )

    def test_period_section_default_rate(self):
        """When no total is provided the first tier must be used."""
        self.assertEqual(self.period_commission.calculate_period_section(), 1.0)

    def test_period_section_by_amount(self):
        """Commission percentage should follow the defined tiers."""
        test_matrix = (
            (50000.0, 1.0),
            (150000.0, 2.0),
            (250000.0, 3.0),
            (350000.0, 4.0),
            (450000.0, 5.0),
        )

        for amount, expected in test_matrix:
            with self.subTest(amount=amount):
                self.assertEqual(
                    self.period_commission.calculate_period_section(amount), expected
                )

    def test_period_section_out_of_range(self):
        """Amounts outside configured tiers should return zero."""
        self.assertEqual(
            self.period_commission.calculate_period_section(-1.0),
            0.0,
        )

