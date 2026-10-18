from datetime import date

from psycopg2 import IntegrityError

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestMonetaryUpdateBasic(TransactionCase):
    def setUp(self):
        super().setUp()
        self.index_model = self.env["monetary.index"]
        self.rate_model = self.env["monetary.index.rate"]
        self.service = self.env["monetary.update.service"]

        # Create test index
        self.test_index = self.index_model.create(
            {
                "name": "Test Index",
                "code": "TEST",
                "authority": "Test Authority",
            }
        )

        # Create test rates
        self.rate_model.create(
            {
                "index_id": self.test_index.id,
                "date": date(2024, 1, 1),
                "value": 1.0,
                "source": "manual",
            }
        )
        self.rate_model.create(
            {
                "index_id": self.test_index.id,
                "date": date(2024, 2, 1),
                "value": 2.0,
                "source": "manual",
            }
        )
        self.rate_model.create(
            {
                "index_id": self.test_index.id,
                "date": date(2024, 3, 1),
                "value": 1.5,
                "source": "manual",
            }
        )

    def test_get_rate_exact(self):
        """Test getting exact rate"""
        rate = self.service.get_rate("TEST", date(2024, 1, 1), policy="exact")
        self.assertEqual(rate, 1.0)

    def test_get_rate_not_found(self):
        """Test getting rate that doesn't exist"""
        rate = self.service.get_rate("TEST", date(2024, 4, 1), policy="exact")
        self.assertIsNone(rate)

    def test_get_rate_use_last_available(self):
        """Test using last available rate"""
        rate = self.service.get_rate(
            "TEST", date(2024, 3, 15), policy="use_last_available"
        )
        self.assertEqual(rate, 1.5)

    def test_get_series(self):
        """Test getting series of rates"""
        series = self.service.get_series("TEST", date(2024, 1, 1), date(2024, 3, 1))
        self.assertEqual(len(series), 3)
        self.assertEqual(series[0][1], 1.0)
        self.assertEqual(series[1][1], 2.0)
        self.assertEqual(series[2][1], 1.5)

    def test_compute_factor_compound(self):
        """Test compound factor computation"""
        factor = self.service.compute_factor(
            "TEST", date(2024, 1, 1), date(2024, 3, 1), mode="compound", missing="error"
        )
        # (1 + 0.01) * (1 + 0.02) * (1 + 0.015) = 1.04654
        expected = 1.01 * 1.02 * 1.015
        self.assertAlmostEqual(factor, expected, places=5)

    def test_compute_factor_simple(self):
        """Test simple factor computation"""
        factor = self.service.compute_factor(
            "TEST", date(2024, 1, 1), date(2024, 3, 1), mode="simple", missing="error"
        )
        # 1 + (1.0 + 2.0 + 1.5) / 100 = 1.045
        expected = 1.0 + (1.0 + 2.0 + 1.5) / 100.0
        self.assertAlmostEqual(factor, expected, places=5)

    def test_compute_factor_no_data_error(self):
        """Test error when no data available"""
        with self.assertRaises(UserError):
            self.service.compute_factor(
                "TEST",
                date(2025, 1, 1),
                date(2025, 3, 1),
                mode="compound",
                missing="error",
            )

    def test_update_amount(self):
        """Test updating amount"""
        original = 1000.0
        updated = self.service.compute_updated_amount(
            "TEST", original, date(2024, 1, 1), date(2024, 3, 1), mode="compound"
        )
        factor = 1.01 * 1.02 * 1.015
        expected = original * factor
        self.assertAlmostEqual(updated, expected, places=2)

    @mute_logger("odoo.sql_db")
    def test_index_code_unique(self):
        """Test that index code is unique per company"""
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.index_model.create(
                {
                    "name": "Duplicate Test Index",
                    "code": "TEST",
                    "authority": "Test Authority",
                }
            )

    @mute_logger("odoo.sql_db")
    def test_rate_date_unique(self):
        """Test that rate date is unique per index"""
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.rate_model.create(
                {
                    "index_id": self.test_index.id,
                    "date": date(2024, 1, 1),
                    "value": 5.0,
                    "source": "manual",
                }
            )
