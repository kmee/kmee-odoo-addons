# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPublicHolidaysWizard(TransactionCase):
    def test_end_date_follows_interval(self):
        wizard = self.env["l10n_br.public.holidays.wizard"].create(
            {
                "start_date": "2026-01-01",
                "interval_number": 2,
                "interval_type": "months",
            }
        )
        self.assertEqual(wizard.end_date, fields.Date.to_date("2026-03-01"))

    def test_import_national_holidays(self):
        wizard = self.env["l10n_br.public.holidays.wizard"].create(
            {
                "start_date": "2026-01-01",
                "interval_number": 0,
                "interval_type": "years",
            }
        )
        self.assertTrue(wizard.import_brazilian_holidays())
        year = self.env["hr.holidays.public"].search(
            [("year", "=", 2026), ("country_id", "=", self.env.ref("base.br").id)]
        )
        self.assertTrue(year)
        self.assertTrue(year.line_ids)
        self.assertTrue(
            year.line_ids.filtered(
                lambda line: line.date.month == 1 and line.date.day == 1
            )
        )
