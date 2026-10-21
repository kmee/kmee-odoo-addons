# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHourInterval5Min(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Hour Employee", "tz": "UTC"}
        )
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Hourly leave",
                "requires_allocation": "no",
                "leave_validation_type": "hr",
                "request_unit": "hour",
            }
        )

    def _selection(self, field_name):
        field = self.env["hr.leave"]._fields[field_name]
        return field._description_selection(self.env)

    def _hourly_leave(self, hour_from, hour_to):
        return self.env["hr.leave"].create(
            {
                "name": "Hourly",
                "employee_id": self.employee.id,
                "holiday_status_id": self.leave_type.id,
                "request_unit_hours": True,
                "request_date_from": "2026-03-02",
                "request_date_to": "2026-03-02",
                "request_hour_from": hour_from,
                "request_hour_to": hour_to,
            }
        )

    def test_selection_has_one_option_every_five_minutes(self):
        """
        Dado o campo request_hour_from
        Quando a selecao e lida
        Entao ha 288 opcoes (24h x 12 fatias de 5 min) em vez das 48 do core
        """
        for name in ("request_hour_from", "request_hour_to"):
            values = [value for value, _label in self._selection(name)]
            self.assertEqual(len(values), 288)
            self.assertEqual(len(set(values)), 288)

    def test_selection_contains_five_minute_slot_and_core_half_hours(self):
        """
        Dado a selecao ampliada
        Quando se procura 08:05 e 08:30
        Entao as duas existem (a de 5 min e a do core, compatibilidade)
        """
        values = [value for value, _label in self._selection("request_hour_from")]
        self.assertIn(str(8 + 5 / 60), values)
        self.assertIn("8.5", values)

    def test_selection_labels_use_twelve_hour_clock(self):
        """
        Dado a selecao ampliada
        Quando os rotulos sao lidos
        Entao 00:00 vira '12:00 AM', 12:05 '12:05 PM' e 13:10 '1:10 PM'
        """
        labels = dict(self._selection("request_hour_from"))
        self.assertEqual(labels["0.0"], "12:00 AM")
        self.assertEqual(labels[str(12 + 5 / 60)], "12:05 PM")
        self.assertEqual(labels[str(13 + 10 / 60)], "1:10 PM")
        self.assertEqual(labels[str(8 + 5 / 60)], "8:05 AM")

    def test_hourly_leave_keeps_minute_precision(self):
        """
        Dado um tipo de folga por hora e um funcionario em UTC
        Quando a folga e pedida de 08:05 ate 09:10
        Entao date_from/date_to saem 08:05 e 09:10 (nao arredondados a 30 min)
        """
        leave = self._hourly_leave("8.5", "9.5")
        leave.write(
            {
                "request_hour_from": str(8 + 5 / 60),
                "request_hour_to": str(9 + 10 / 60),
            }
        )
        self.assertEqual(leave.request_hour_from, str(8 + 5 / 60))
        self.assertEqual(leave.date_from, datetime(2026, 3, 2, 8, 5))
        self.assertEqual(leave.date_to, datetime(2026, 3, 2, 9, 10))
