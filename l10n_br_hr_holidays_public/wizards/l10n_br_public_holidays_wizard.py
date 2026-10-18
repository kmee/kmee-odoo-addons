# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

import pytz
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

from odoo.addons.l10n_br_resource.tools.brazil_all_holidays_set import (
    brazil_all_holidays_set,
)

_logger = logging.getLogger(__name__)

_INTERVALS = {
    "days": lambda interval: relativedelta(days=interval),
    "weeks": lambda interval: relativedelta(days=7 * interval),
    "months": lambda interval: relativedelta(months=interval),
    "years": lambda interval: relativedelta(months=12 * interval),
}


class L10n_brPublicHolidaysWizard(models.TransientModel):

    _name = "l10n_br.public.holidays.wizard"
    _description = "Brazilian Public Holidays Import Wizard"

    start_date = fields.Date(default=fields.Date.today)
    end_date = fields.Date(compute="_compute_end_date", readonly=False)
    interval_number = fields.Integer(string="Interval", default=1)
    interval_type = fields.Selection(
        [
            ("days", "Dia(s)"),
            ("weeks", "Semana(s)"),
            ("months", "Mês(es)"),
            ("years", "Ano(s)"),
        ],
        string="Tipo",
        default="years",
        required=True,
    )
    state_id = fields.Many2one("res.country.state", string="Estado")
    city_id = fields.Many2one(
        "res.city", string="Cidade", domain="[('state_id', '=', state_id)]"
    )

    @api.depends("start_date", "interval_number", "interval_type")
    def _compute_end_date(self):
        for wiz in self:
            wiz.end_date = fields.Date.to_date(wiz.start_date) + _INTERVALS[
                wiz.interval_type
            ](wiz.interval_number)

    def import_brazilian_holidays(self):
        tz_br = pytz.timezone("America/Sao_Paulo")
        for wiz in self:
            date_reference = fields.Date.to_date(wiz.start_date)
            while date_reference.year <= fields.Date.to_date(wiz.end_date).year:
                all_holidays = brazil_all_holidays_set(date_reference.year)
                for holiday in all_holidays:
                    self._create_holiday_record(holiday, tz_br)
                date_reference += relativedelta(years=1)
        return True

    def _create_holiday_record(self, holiday, tz_br):
        brazil = self.env.ref("base.br")
        year_id = self.env["calendar.public.holiday"].search(
            [("year", "=", holiday.date.year), ("country_id", "=", brazil.id)],
            limit=1,
        )
        if not year_id:
            year_id = self.env["calendar.public.holiday"].create(
                {"year": holiday.date.year, "country_id": brazil.id}
            )

        # Prepare and localize the holiday date
        utc_dt = fields.Datetime.to_datetime(fields.Datetime.to_datetime(holiday.date))
        user_dt = tz_br.localize(utc_dt)
        holiday_date = utc_dt - relativedelta(
            seconds=user_dt.utcoffset().total_seconds()
        )

        # Create the holiday line
        line_values = {
            "name": holiday.name,
            "date": fields.Date.to_date(holiday_date),
            "public_holiday_id": year_id.id,
            "variable_date": False,
        }

        if holiday.state_ibge:
            state = self.env["res.country.state"].search(
                [("ibge_code", "=", holiday.state_ibge)], limit=1
            )
            if state and state == self.state_id:
                line_values.update({"state_ids": [(6, 0, [state.id])]})
            else:
                return

            if holiday.city_ibge:
                city = self.env["res.city"].search(
                    [("ibge_code", "=", holiday.city_ibge)], limit=1
                )
                if city and city == self.city_id:
                    line_values.update({"city_ids": [(6, 0, [city.id])]})
                else:
                    return

        self.env["calendar.public.holiday.line"].create(line_values)
