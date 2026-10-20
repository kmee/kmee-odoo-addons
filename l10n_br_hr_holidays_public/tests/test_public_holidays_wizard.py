# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPublicHolidaysWizard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.br = cls.env.ref("base.br")
        cls.wizard_model = cls.env["l10n_br.public.holidays.wizard"]
        cls.state_sp = cls.env["res.country.state"].search(
            [("code", "=", "SP"), ("country_id", "=", cls.br.id)], limit=1
        )
        cls.state_rj = cls.env["res.country.state"].search(
            [("code", "=", "RJ"), ("country_id", "=", cls.br.id)], limit=1
        )
        cls.city_sp = cls.env["res.city"].search(
            [("ibge_code", "=", "3550308")], limit=1
        ) or cls.env["res.city"].create(
            {
                "name": "Sao Paulo",
                "state_id": cls.state_sp.id,
                "country_id": cls.br.id,
                "ibge_code": "3550308",
            }
        )

    def _wizard(self, **vals):
        values = {
            "start_date": "2026-01-01",
            "interval_number": 0,
            "interval_type": "years",
        }
        values.update(vals)
        return self.wizard_model.create(values)

    def _lines(self, year=2026):
        return self.env["calendar.public.holiday.line"].search(
            [
                ("public_holiday_id.year", "=", year),
                ("public_holiday_id.country_id", "=", self.br.id),
            ]
        )

    def test_end_date_follows_interval_type(self):
        """
        Given a start date of 2026-01-01
        When the interval is 10 days, 2 weeks, 2 months or 2 years
        Then end_date is start plus that interval
        """
        expected = {
            ("days", 10): "2026-01-11",
            ("weeks", 2): "2026-01-15",
            ("months", 2): "2026-03-01",
            ("years", 2): "2028-01-01",
        }
        for (interval_type, number), end in expected.items():
            wizard = self._wizard(interval_number=number, interval_type=interval_type)
            self.assertEqual(
                wizard.end_date, fields.Date.to_date(end), (interval_type, number)
            )

    def test_end_date_recomputed_when_interval_changes(self):
        """
        Given a wizard with a 1 year interval
        When the interval type changes to months
        Then end_date is recomputed
        """
        wizard = self._wizard(interval_number=1)
        self.assertEqual(wizard.end_date, fields.Date.to_date("2027-01-01"))
        wizard.interval_type = "months"
        self.assertEqual(wizard.end_date, fields.Date.to_date("2026-02-01"))

    def test_import_creates_year_with_national_holidays(self):
        """
        Given no public holiday year for 2026
        When Brazilian holidays are imported for 2026
        Then a Brazil year 2026 exists with the national holidays, without
        state or city restriction
        """
        self.assertFalse(self._lines())
        self.assertTrue(self._wizard().import_brazilian_holidays())
        lines = self._lines()
        by_date = {line.date.isoformat(): line for line in lines}
        for national in ("2026-01-01", "2026-04-21", "2026-09-07", "2026-12-25"):
            self.assertIn(national, by_date)
            self.assertFalse(by_date[national].state_ids)
            self.assertFalse(by_date[national].city_ids)
        self.assertFalse(by_date["2026-01-01"].variable_date)

    def test_import_skips_state_holidays_without_state(self):
        """
        Given no state selected in the wizard
        When holidays are imported
        Then regional holidays (Sao Paulo, 9 July) are not created
        """
        self._wizard().import_brazilian_holidays()
        self.assertNotIn(
            fields.Date.to_date("2026-07-09"), self._lines().mapped("date")
        )
        self.assertFalse(self._lines().filtered(lambda line: line.state_ids))

    def test_import_state_holidays_for_selected_state(self):
        """
        Given the state Sao Paulo selected
        When holidays are imported
        Then the 9 July holiday exists restricted to SP, and holidays of
        other states (RJ) are not created
        """
        self._wizard(state_id=self.state_sp.id).import_brazilian_holidays()
        lines = self._lines()
        july = lines.filtered(
            lambda line: line.date == fields.Date.to_date("2026-07-09")
        )
        self.assertTrue(july)
        self.assertEqual(july.state_ids, self.state_sp)
        self.assertFalse(lines.filtered(lambda line: self.state_rj in line.state_ids))

    def test_import_city_holidays_for_selected_city(self):
        """
        Given the city Sao Paulo selected
        When holidays are imported
        Then the city anniversary (25 January) is restricted to that city
        """
        self._wizard(
            state_id=self.state_sp.id, city_id=self.city_sp.id
        ).import_brazilian_holidays()
        lines = self._lines()
        city_lines = lines.filtered(lambda line: self.city_sp in line.city_ids)
        self.assertTrue(city_lines)
        self.assertIn(fields.Date.to_date("2026-01-25"), city_lines.mapped("date"))
        self.assertEqual(city_lines.mapped("state_ids"), self.state_sp)

    def test_import_without_city_skips_city_holidays(self):
        """
        Given only the state selected (no city)
        When holidays are imported
        Then no city holiday is created
        """
        self._wizard(state_id=self.state_sp.id).import_brazilian_holidays()
        self.assertFalse(self._lines().filtered(lambda line: line.city_ids))

    def test_import_multiple_years_creates_one_year_each(self):
        """
        Given an interval of 1 year starting on 2026-01-01
        When holidays are imported
        Then public holiday years 2026 and 2027 are created, once each
        """
        self._wizard(interval_number=1).import_brazilian_holidays()
        years = self.env["calendar.public.holiday"].search(
            [("country_id", "=", self.br.id), ("year", "in", (2026, 2027))]
        )
        self.assertEqual(sorted(years.mapped("year")), [2026, 2027])
        self.assertTrue(self._lines(2027))

    def test_import_reuses_existing_year(self):
        """
        Given the year 2026 already exists
        When holidays are imported
        Then the same year record is reused (no duplicate year)
        """
        year = self.env["calendar.public.holiday"].create(
            {"year": 2026, "country_id": self.br.id}
        )
        self._wizard().import_brazilian_holidays()
        years = self.env["calendar.public.holiday"].search(
            [("year", "=", 2026), ("country_id", "=", self.br.id)]
        )
        self.assertEqual(years, year)
        self.assertTrue(year.line_ids)

    def test_menu_opens_brazilian_wizard(self):
        """
        Given the module is installed
        When the 'create next year' public holidays menu is read
        Then it opens the Brazilian import wizard action
        """
        menu = self.env.ref("hr_holidays_public.menu_create_next_year_public_holidays")
        action = self.env.ref(
            "l10n_br_hr_holidays_public.l10n_br_public_holidays_wizard_act_window"
        )
        self.assertEqual(menu.action, action)
        self.assertEqual(action.res_model, "l10n_br.public.holidays.wizard")

    def test_wizard_requires_holiday_manager(self):
        """
        Given a plain internal user without the holidays manager group
        When he tries to create the wizard
        Then access is denied; a holidays manager can create it
        """
        user = self.env["res.users"].create(
            {
                "name": "Plain",
                "login": "plain_hol",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(AccessError):
            self.wizard_model.with_user(user).create({})
        manager = self.env["res.users"].create(
            {
                "name": "Manager",
                "login": "manager_hol",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("hr_holidays.group_hr_holidays_manager").id,
                        ],
                    )
                ],
            }
        )
        self.assertTrue(self.wizard_model.with_user(manager).create({}))

    def test_wizard_form_has_no_stray_text(self):
        """
        Given the wizard form view
        When its architecture is parsed
        Then the form root has no loose text node (a stray character would be
        rendered on screen)
        """
        view = self.env.ref(
            "l10n_br_hr_holidays_public.l10n_br_public_holidays_wizard_form_view"
        )
        root = etree.fromstring(view.arch.encode())
        self.assertEqual((root.text or "").strip(), "")
