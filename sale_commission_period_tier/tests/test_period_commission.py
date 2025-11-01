from odoo.tests.common import SavepointCase


class TestPeriodCommission(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.period_commission = cls.env["sale.commission"].create(
            {
                "name": "Period Commission Test",
                "commission_type": "period_section",
                "invoice_state": "open",
                "amount_base_type": "gross_amount",
                "section_ids": [
                    (0, 0, {"amount_from": 0.0, "amount_to": 100000.0, "percent": 1.0}),
                    (0, 0, {"amount_from": 100000.0, "amount_to": 200000.0, "percent": 2.0}),
                    (0, 0, {"amount_from": 200000.0, "amount_to": 300000.0, "percent": 3.0}),
                    (0, 0, {"amount_from": 300000.0, "amount_to": 400000.0, "percent": 4.0}),
                    (0, 0, {"amount_from": 400000.0, "amount_to": False, "percent": 5.0}),
                ],
            }
        )

    def test_calculate_period_section_without_total(self):
        self.assertEqual(self.period_commission.calculate_period_section(), 1.0)

    def test_calculate_period_section_first_tier(self):
        self.assertEqual(
            self.period_commission.calculate_period_section(50000.0),
            1.0,
        )

    def test_calculate_period_section_middle_tier(self):
        self.assertEqual(
            self.period_commission.calculate_period_section(150000.0),
            2.0,
        )

    def test_calculate_period_section_last_tier(self):
        self.assertEqual(
            self.period_commission.calculate_period_section(450000.0),
            5.0,
        )

    def test_calculate_period_section_no_sections(self):
        commission = self.env["sale.commission"].create(
            {
                "name": "Empty Period Commission",
                "commission_type": "period_section",
                "invoice_state": "open",
                "amount_base_type": "gross_amount",
            }
        )
        self.assertEqual(commission.calculate_period_section(1000.0), 0.0)
