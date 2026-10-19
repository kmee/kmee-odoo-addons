# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date
from unittest.mock import patch

import requests
from freezegun import freeze_time

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

REQUESTS_GET = (
    "odoo.addons.monetary_index_update_selic.models."
    "monetary_index_provider.requests.get"
)


class FakeResponse:
    def __init__(self, payload=None, error=None, json_error=None):
        self._payload = payload
        self._error = error
        self._json_error = json_error

    def raise_for_status(self):
        if self._error:
            raise self._error

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._payload


@tagged("post_install", "-at_install")
class TestSelicBehavior(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.provider = cls.env["monetary.index.provider"]
        cls.index = cls.env.ref("monetary_index_update_selic.monetary_index_selic")
        cls.rate_model = cls.env["monetary.index.rate"]

    def _rates(self):
        return self.rate_model.search([("index_id", "=", self.index.id)])

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------
    def test_selic_index_is_seeded(self):
        """Given the module installed, Then the SELIC index of BCB exists for
        Brazil."""
        self.assertEqual(self.index.code, "SELIC")
        self.assertEqual(self.index.authority, "BCB")
        self.assertEqual(self.index.country_id, self.env.ref("base.br"))

    def test_daily_cron_is_active_and_calls_the_provider(self):
        """Given the cron seed, Then it runs daily on the provider method as
        the superuser."""
        cron = self.env.ref("monetary_index_update_selic.ir_cron_update_selic_rates")
        self.assertTrue(cron.active)
        self.assertEqual(cron.interval_type, "days")
        self.assertIn("cron_update_selic_rates", cron.code)
        self.assertEqual(cron.model_id.model, "monetary.index.provider")
        self.assertEqual(cron.user_id, self.env.ref("base.user_root"))

    # ------------------------------------------------------------------
    # Provider
    # ------------------------------------------------------------------
    def test_index_not_found_raises(self):
        """Given the SELIC index deleted, When updating, Then UserError and no
        HTTP call is made."""
        self.index.unlink()
        with patch(REQUESTS_GET) as mock_get:
            with self.assertRaises(UserError):
                self.provider.update_selic_rates()
        mock_get.assert_not_called()

    def test_bcb_params_use_brazilian_date_format(self):
        """Given dates, Then BCB params use dd/mm/yyyy; without dates only the
        format is sent."""
        params = self.provider._build_bcb_params(date(2025, 1, 2), date(2025, 3, 31))
        self.assertEqual(
            params,
            {"formato": "json", "dataInicial": "02/01/2025", "dataFinal": "31/03/2025"},
        )
        self.assertEqual(
            self.provider._build_bcb_params(None, None), {"formato": "json"}
        )

    @mute_logger(
        "odoo.addons.monetary_index_update_selic.models.monetary_index_provider"
    )
    def test_http_failure_becomes_user_error(self):
        """Given the BCB is down (connection error, HTTP error or invalid JSON),
        Then the user gets a UserError and no rate is created."""
        failures = (
            requests.ConnectionError("down"),
            FakeResponse(error=requests.HTTPError("500")),
            FakeResponse(json_error=ValueError("bad json")),
        )
        for failure in failures:
            kwargs = (
                {"side_effect": failure}
                if isinstance(failure, Exception)
                else {"return_value": failure}
            )
            with patch(REQUESTS_GET, **kwargs), self.assertRaises(UserError):
                self.provider.update_selic_rates()
        self.assertFalse(self._rates())

    def test_unexpected_payload_is_refused(self):
        """Given the BCB answers a dict instead of a list, Then UserError."""
        with patch(REQUESTS_GET, return_value=FakeResponse({"erro": "x"})):
            with self.assertRaises(UserError):
                self.provider.update_selic_rates()

    @mute_logger(
        "odoo.addons.monetary_index_update_selic.models.monetary_index_provider"
    )
    def test_parse_skips_invalid_entries(self):
        """Given a payload with bad date, bad value and missing keys, Then only
        the valid entry is parsed (comma decimal accepted)."""
        payload = [
            {"data": "02/01/2025", "valor": "0,043225"},
            {"data": "2025-01-03", "valor": "0.1"},
            {"data": "04/01/2025", "valor": "abc"},
            {"valor": "0.1"},
            {"data": "05/01/2025"},
        ]
        parsed = self.provider._parse_bcb_payload(payload)
        self.assertEqual(parsed, [(date(2025, 1, 2), 0.043225)])

    def test_update_sends_the_period_and_marks_rates_as_api(self):
        """Given a period, When updating, Then the BCB receives it and the new
        rates are stored with source api and note BCB."""
        payload = [{"data": "02/01/2025", "valor": "0.05"}]
        with patch(REQUESTS_GET, return_value=FakeResponse(payload)) as mock_get:
            result = self.provider.update_selic_rates(
                date_from=date(2025, 1, 1), date_to=date(2025, 1, 31)
            )
        self.assertEqual(
            mock_get.call_args.kwargs["params"]["dataInicial"], "01/01/2025"
        )
        self.assertEqual(mock_get.call_args.kwargs["params"]["dataFinal"], "31/01/2025")
        self.assertEqual(result, {"created": 1, "updated": 0, "skipped": 0, "total": 1})
        rate = self._rates()
        self.assertEqual((rate.source, rate.note), ("api", "BCB"))
        self.assertAlmostEqual(rate.value, 0.05, places=6)

    def test_same_value_is_skipped_unless_forced(self):
        """Given a stored rate equal to the BCB one, When updating, Then it is
        skipped; with force it is rewritten as api."""
        rate = self.rate_model.create(
            {
                "index_id": self.index.id,
                "date": date(2025, 1, 2),
                "value": 0.05,
                "source": "manual",
            }
        )
        payload = [{"data": "02/01/2025", "valor": "0.05"}]
        with patch(REQUESTS_GET, return_value=FakeResponse(payload)):
            result = self.provider.update_selic_rates()
        self.assertEqual((result["skipped"], result["updated"]), (1, 0))
        self.assertEqual(rate.source, "manual")
        with patch(REQUESTS_GET, return_value=FakeResponse(payload)):
            result = self.provider.update_selic_rates(force=True)
        self.assertEqual((result["skipped"], result["updated"]), (0, 1))
        self.assertEqual(rate.source, "api")

    def test_cron_fetches_from_first_day_of_previous_month(self):
        """Given today is 2025-03-20, When the cron runs, Then it asks the BCB
        from 01/02/2025 to 20/03/2025."""
        with freeze_time("2025-03-20"), patch(
            REQUESTS_GET, return_value=FakeResponse([])
        ) as mock_get:
            result = self.provider.cron_update_selic_rates()
        params = mock_get.call_args.kwargs["params"]
        self.assertEqual(
            (params["dataInicial"], params["dataFinal"]), ("01/02/2025", "20/03/2025")
        )
        self.assertEqual(result["total"], 0)

    # ------------------------------------------------------------------
    # Wizard
    # ------------------------------------------------------------------
    def test_wizard_defaults_to_previous_month_until_today(self):
        """Given today is 2025-03-20, Then the wizard starts on 2025-02-01 and
        ends today."""
        with freeze_time("2025-03-20"):
            defaults = self.env["monetary.index.selic.update.wizard"].default_get(
                ["date_from", "date_to"]
            )
        self.assertEqual(defaults["date_from"], date(2025, 2, 1))
        self.assertEqual(defaults["date_to"], date(2025, 3, 20))
        wizard = self.env["monetary.index.selic.update.wizard"].create({})
        self.assertFalse(wizard.force)

    def test_wizard_refuses_inverted_period(self):
        """Given date_from after date_to, When updating, Then UserError and no
        HTTP call."""
        wizard = self.env["monetary.index.selic.update.wizard"].create(
            {"date_from": date(2025, 2, 1), "date_to": date(2025, 1, 1)}
        )
        with patch(REQUESTS_GET) as mock_get, self.assertRaises(UserError):
            wizard.action_update()
        mock_get.assert_not_called()

    def test_wizard_reports_counts_in_notification(self):
        """Given two new rates from the BCB, When the manager confirms, Then
        the notification reports 2 created and the rates exist."""
        payload = [
            {"data": "02/01/2025", "valor": "0.05"},
            {"data": "03/01/2025", "valor": "0.06"},
        ]
        wizard = self.env["monetary.index.selic.update.wizard"].create(
            {"date_from": date(2025, 1, 1), "date_to": date(2025, 1, 31)}
        )
        with patch(REQUESTS_GET, return_value=FakeResponse(payload)):
            action = wizard.action_update()
        self.assertEqual(action["tag"], "display_notification")
        self.assertIn("Criados: 2", action["params"]["message"])
        self.assertEqual(len(self._rates()), 2)

    def test_wizard_force_flag_reaches_the_provider(self):
        """Given force checked and an equal stored rate, Then it is counted as
        updated, not skipped."""
        self.rate_model.create(
            {"index_id": self.index.id, "date": date(2025, 1, 2), "value": 0.05}
        )
        wizard = self.env["monetary.index.selic.update.wizard"].create(
            {
                "date_from": date(2025, 1, 1),
                "date_to": date(2025, 1, 31),
                "force": True,
            }
        )
        payload = [{"data": "02/01/2025", "valor": "0.05"}]
        with patch(REQUESTS_GET, return_value=FakeResponse(payload)):
            action = wizard.action_update()
        self.assertIn("Atualizados: 1", action["params"]["message"])

    def test_only_managers_can_open_the_wizard(self):
        """Given an internal user outside the monetary groups, Then creating the
        wizard is denied; a monetary manager can."""
        group_manager = self.env.ref(
            "monetary_index_update.group_monetary_update_manager"
        )
        plain = self.env["res.users"].create(
            {
                "name": "Plain",
                "login": "selic_plain",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        manager = self.env["res.users"].create(
            {
                "name": "Mgr",
                "login": "selic_mgr",
                "groups_id": [(6, 0, [group_manager.id])],
            }
        )
        model = self.env["monetary.index.selic.update.wizard"]
        with self.assertRaises(AccessError):
            model.with_user(plain).create({})
        self.assertTrue(model.with_user(manager).create({}).exists())

    def test_form_button_only_for_selic_index(self):
        """Given the index form, Then the update button is bound to the SELIC
        code only."""
        view = self.env.ref(
            "monetary_index_update_selic.view_monetary_index_form_selic"
        )
        self.assertIn(
            "'invisible': [('code', '!=', 'SELIC')]", view.arch_db.replace('"', "'")
        )
