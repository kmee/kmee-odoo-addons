# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date
from unittest.mock import patch

from freezegun import freeze_time

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMonetaryUpdateBehavior(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.index_model = cls.env["monetary.index"]
        cls.rate_model = cls.env["monetary.index.rate"]
        cls.service = cls.env["monetary.update.service"]
        cls.index = cls.index_model.create({"name": "Behavior", "code": "BEH"})
        cls.rates = cls.env["monetary.index.rate"]
        for month, value in ((1, 1.0), (2, 2.0), (3, 1.5)):
            cls.rates |= cls.rate_model.create(
                {"index_id": cls.index.id, "date": date(2024, month, 1), "value": value}
            )
        group_user = cls.env.ref("monetary_index_update.group_monetary_update_user")
        group_manager = cls.env.ref(
            "monetary_index_update.group_monetary_update_manager"
        )
        cls.user = cls.env["res.users"].create(
            {
                "name": "Monetary User",
                "login": "monetary_user",
                "groups_id": [(6, 0, [group_user.id])],
            }
        )
        cls.manager = cls.env["res.users"].create(
            {
                "name": "Monetary Manager",
                "login": "monetary_manager",
                "groups_id": [(6, 0, [group_manager.id])],
            }
        )

    def _wizard(self, field_names=("value",), record=None, **vals):
        record = record or self.rates[0]
        model = self.env["ir.model"]._get("monetary.index.rate")
        values = {
            "model_id": model.id,
            "res_id": record.id,
            "index_id": self.index.id,
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 3, 1),
        }
        values.update(vals)
        return (
            self.env["monetary.update.by.index.wizard"]
            .with_context(field_names=list(field_names))
            .create(values)
        )

    # ------------------------------------------------------------------
    # Index and rate constraints
    # ------------------------------------------------------------------
    def test_index_code_is_unique_case_insensitive(self):
        """Given index BEH, When creating 'beh' in the same company, Then it is
        refused; a different code is accepted (negative control)."""
        with self.assertRaises(ValidationError):
            self.index_model.create({"name": "Dup", "code": "beh"})
        other = self.index_model.create({"name": "Other", "code": "OTHER"})
        self.assertTrue(other.exists())

    def test_index_code_cannot_be_blank(self):
        """Given a code made only of spaces, Then the index is refused."""
        with self.assertRaises(ValidationError):
            self.index_model.create({"name": "Blank", "code": "   "})

    def test_same_code_is_allowed_in_another_company(self):
        """Given index BEH of company A, When company B creates BEH, Then both
        coexist because uniqueness is per company."""
        company_b = self.env["res.company"].create({"name": "Other Co"})
        other = self.index_model.create(
            {"name": "Beh B", "code": "BEH", "company_id": company_b.id}
        )
        self.assertNotEqual(other.company_id, self.index.company_id)

    def test_rate_below_minus_100_is_refused(self):
        """Given a rate of -100.01 percent, Then it is refused; -100 is the
        accepted lower bound."""
        with self.assertRaises(ValidationError):
            self.rate_model.create(
                {"index_id": self.index.id, "date": date(2024, 5, 1), "value": -100.01}
            )
        ok = self.rate_model.create(
            {"index_id": self.index.id, "date": date(2024, 5, 1), "value": -100.0}
        )
        self.assertEqual(ok.value, -100.0)

    def test_deleting_index_deletes_its_rates(self):
        """Given an index with rates, When the index is deleted, Then the rates
        are deleted too (ondelete cascade)."""
        rates = self.rates
        self.index.unlink()
        self.assertFalse(rates.exists())

    # ------------------------------------------------------------------
    # Service
    # ------------------------------------------------------------------
    def test_index_lookup_is_case_insensitive(self):
        """Given index BEH, When asking for the rate with code 'beh', Then the
        rate is found."""
        self.assertEqual(self.service.get_rate("beh", date(2024, 2, 1)), 2.0)

    def test_unknown_index_raises_user_error(self):
        """Given an unknown code, Then rate, series and factor raise UserError."""
        with self.assertRaises(UserError):
            self.service.get_rate("NOPE", date(2024, 1, 1))
        with self.assertRaises(UserError):
            self.service.get_series("NOPE", date(2024, 1, 1), date(2024, 2, 1))
        with self.assertRaises(UserError):
            self.service.compute_factor("NOPE", date(2024, 1, 1), date(2024, 2, 1))

    def test_last_available_policy_needs_a_previous_rate(self):
        """Given a date before the first rate, When using last available, Then
        None is returned (there is nothing to fall back to)."""
        self.assertIsNone(
            self.service.get_rate("BEH", date(2023, 12, 1), policy="use_last_available")
        )
        # Control: exact policy does not fall back even when a previous exists
        self.assertIsNone(self.service.get_rate("BEH", date(2024, 3, 15)))

    def test_series_respects_the_interval_and_order(self):
        """Given three monthly rates, When asking Feb to Mar, Then only those
        two come, in ascending date order."""
        series = self.service.get_series("BEH", date(2024, 2, 1), date(2024, 3, 1))
        self.assertEqual(series, [(date(2024, 2, 1), 2.0), (date(2024, 3, 1), 1.5)])

    def test_compute_factor_rejects_invalid_arguments(self):
        """Given an invalid mode or missing policy, Then UserError is raised."""
        with self.assertRaises(UserError):
            self.service.compute_factor(
                "BEH", date(2024, 1, 1), date(2024, 3, 1), mode="weird"
            )
        with self.assertRaises(UserError):
            self.service.compute_factor(
                "BEH", date(2024, 1, 1), date(2024, 3, 1), missing="weird"
            )

    def test_compute_factor_without_rates_and_skip_policy(self):
        """Given a period without rates, When missing='skip', Then the factor
        is neutral (1.0) instead of raising; with 'error' it raises."""
        factor = self.service.compute_factor(
            "BEH", date(2030, 1, 1), date(2030, 3, 1), missing="skip"
        )
        self.assertEqual(factor, 1.0)
        with self.assertRaises(UserError):
            self.service.compute_factor("BEH", date(2030, 1, 1), date(2030, 3, 1))

    def test_updated_amount_simple_mode(self):
        """Given 1000 and the Jan-Mar rates, When updating in simple mode, Then
        the amount grows by the sum of the rates (4.5 percent)."""
        amount = self.service.compute_updated_amount(
            "BEH", 1000.0, date(2024, 1, 1), date(2024, 3, 1), mode="simple"
        )
        self.assertAlmostEqual(amount, 1045.0, places=4)
        compound = self.service.compute_updated_amount(
            "BEH", 1000.0, date(2024, 1, 1), date(2024, 3, 1)
        )
        self.assertNotAlmostEqual(compound, amount, places=2)

    def test_negative_rate_reduces_the_amount(self):
        """Given a deflation of -10 percent, Then the updated amount shrinks."""
        self.rate_model.create(
            {"index_id": self.index.id, "date": date(2024, 4, 1), "value": -10.0}
        )
        amount = self.service.compute_updated_amount(
            "BEH", 100.0, date(2024, 4, 1), date(2024, 4, 1)
        )
        self.assertAlmostEqual(amount, 90.0, places=4)

    def test_unregistered_strategy_raises_user_error(self):
        """Given no registered strategy, When asking for a factor by strategy,
        Then the user gets a clear UserError (not a KeyError)."""
        with self.assertRaises(UserError):
            self.service.compute_factor_with_strategy(
                "BEH", date(2024, 1, 1), date(2024, 3, 1), "does_not_exist"
            )

    def test_service_wizard_action_requires_an_existing_record(self):
        """Given an id that does not exist, When opening the wizard through the
        service, Then a UserError says the record was not found."""
        with self.assertRaises(UserError):
            self.service.monetary_update_fields_by_index_wizard([0])

    # ------------------------------------------------------------------
    # Wizard
    # ------------------------------------------------------------------
    def test_wizard_preview_shows_updated_value_and_percentage(self):
        """Given a record with value 1.0 and the index Jan-Mar, When the wizard
        computes the preview, Then it shows the updated amount and the gain."""
        wizard = self._wizard()
        # factor Jan-Mar = 1.01 * 1.02 * 1.015 = 1.0457
        self.assertIn("Value (%)", wizard.result_preview)
        self.assertIn("1.05", wizard.result_preview)
        self.assertIn("+4.57%", wizard.result_preview)

    def test_wizard_preview_is_empty_without_dates(self):
        """Given a wizard without start date, Then there is no preview."""
        wizard = self._wizard(start_date=False)
        self.assertEqual(wizard.result_preview, "")

    def test_wizard_update_writes_new_values_and_update_date(self):
        """Given a wizard, When the user confirms, Then the tracked field gets
        the updated amount and last_monetary_update_date is the end date."""
        wizard = self._wizard()
        factor = 1.01 * 1.02 * 1.015
        with patch.object(
            type(self.rates[0]), "write", autospec=True, return_value=True
        ) as write:
            wizard.update_fields_by_index()
        write.assert_called_once()
        vals = write.call_args[0][1]
        self.assertAlmostEqual(vals["value"], 1.0 * factor, places=5)
        self.assertEqual(vals["last_monetary_update_date"], date(2024, 3, 1))

    def test_wizard_refuses_field_without_amount(self):
        """Given a tracked field with no amount (0.0), When computing, Then a
        UserError says the amount is not set (not an AttributeError)."""
        zero = self.rate_model.create(
            {"index_id": self.index.id, "date": date(2024, 6, 1), "value": 0.0}
        )
        wizard = self._wizard(record=zero)
        with self.assertRaises(UserError):
            wizard.update_fields_by_index()

    def test_wizard_refuses_missing_record(self):
        """Given a wizard pointing to a deleted record, Then UserError."""
        wizard = self._wizard()
        wizard.res_id = 0
        with self.assertRaises(UserError):
            wizard.update_fields_by_index()

    def test_wizard_end_date_defaults_to_today(self):
        """Given the wizard is opened on another day, Then the default end date
        is that day (and not the day the server was started)."""
        with freeze_time("2031-05-17"):
            defaults = self.env["monetary.update.by.index.wizard"].default_get(
                ["end_date"]
            )
        self.assertEqual(defaults["end_date"], date(2031, 5, 17))

    # ------------------------------------------------------------------
    # Security and views
    # ------------------------------------------------------------------
    def test_user_reads_but_cannot_write_indexes_and_rates(self):
        """Given a plain monetary user, Then reading works, creating and
        editing do not; the manager can do both."""
        index = self.index.with_user(self.user)
        self.assertEqual(index.name, "Behavior")
        self.assertEqual(len(index.rate_ids), 3)
        with self.assertRaises(AccessError):
            index.write({"name": "Hacked"})
        with self.assertRaises(AccessError):
            self.rate_model.with_user(self.user).create(
                {"index_id": self.index.id, "date": date(2024, 9, 1), "value": 1.0}
            )
        self.index.with_user(self.manager).write({"name": "Renamed"})
        self.assertEqual(self.index.name, "Renamed")

    def test_user_cannot_delete_rates(self):
        """Given a monetary user, When deleting a rate, Then access is denied."""
        with self.assertRaises(AccessError):
            self.rates[0].with_user(self.user).unlink()

    def test_other_company_index_is_invisible(self):
        """Given an index of company B, Then the user restricted to company A
        does not see it (multi-company rule)."""
        company_b = self.env["res.company"].create({"name": "Hidden Co"})
        hidden = self.index_model.create(
            {"name": "Hidden", "code": "HID", "company_id": company_b.id}
        )
        visible = self.index_model.with_user(self.user).search([])
        self.assertIn(self.index, visible)
        self.assertNotIn(hidden, visible)
