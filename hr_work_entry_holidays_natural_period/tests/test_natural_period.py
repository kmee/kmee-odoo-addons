# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestNaturalPeriod(TransactionCase):
    """Sexta 02/01/2026 a segunda 05/01/2026: 2 dias uteis (sex e seg) mas
    4 dias corridos (sex, sab, dom, seg)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Natural Employee", "tz": "UTC"}
        )
        cls.work_day_type = cls._leave_type("Working days", "day")
        cls.natural_type = cls._leave_type("Natural days", "natural_day")
        cls.natural_half_type = cls._leave_type(
            "Natural half days", "natural_day_half_day"
        )
        cls.date_from = datetime(2026, 1, 2, 8, 0)
        cls.date_to = datetime(2026, 1, 5, 17, 0)

    @classmethod
    def _leave_type(cls, name, request_unit):
        return cls.env["hr.leave.type"].create(
            {
                "name": name,
                "requires_allocation": "no",
                "leave_validation_type": "hr",
                "request_unit": request_unit,
            }
        )

    def _leave(self, leave_type, **extra):
        vals = {
            "name": "Leave",
            "employee_id": self.employee.id,
            "holiday_status_id": leave_type.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "request_date_from": "2026-01-02",
            "request_date_to": "2026-01-05",
        }
        vals.update(extra)
        return self.env["hr.leave"].create(vals)

    def test_batch_counts_natural_days_when_context_asks_for_it(self):
        """
        Dado o contexto natural_period e um periodo sexta a segunda
        Quando se calcula o numero de dias em lote
        Entao contam 4 dias (finais de semana incluidos)
        """
        leave_model = self.env["hr.leave"].with_context(natural_period=True)
        result = leave_model._get_number_of_days_batch(
            self.date_from, self.date_to, self.employee.ids
        )
        self.assertEqual(result[self.employee.id]["days"], 4)

    def test_batch_counts_working_days_without_context(self):
        """
        Dado o mesmo periodo sem o contexto natural_period
        Quando se calcula o numero de dias em lote
        Entao contam so os 2 dias uteis (sexta e segunda)
        """
        result = self.env["hr.leave"]._get_number_of_days_batch(
            self.date_from, self.date_to, self.employee.ids
        )
        self.assertEqual(result[self.employee.id]["days"], 2)

    def test_batch_returns_one_entry_per_employee(self):
        """
        Dado dois funcionarios
        Quando se calcula o numero de dias em lote
        Entao o resultado traz uma entrada por funcionario com dias e horas
        """
        other = self.env["hr.employee"].create({"name": "Other", "tz": "UTC"})
        result = self.env["hr.leave"]._get_number_of_days_batch(
            self.date_from, self.date_to, (self.employee | other).ids
        )
        self.assertEqual(set(result), {self.employee.id, other.id})
        for data in result.values():
            self.assertIn("days", data)
            self.assertGreater(data["hours"], 0)

    def test_natural_leave_counts_calendar_days(self):
        """
        Dado um tipo de folga 'dia corrido'
        Quando a folga de sexta a segunda e criada
        Entao number_of_days e 4
        """
        self.assertEqual(self._leave(self.natural_type).number_of_days, 4)

    def test_regular_leave_counts_working_days(self):
        """
        Dado um tipo de folga comum ('dia')
        Quando a mesma folga e criada
        Entao number_of_days e 2 (controle: tipo comum nao vira corrido)
        """
        self.assertEqual(self._leave(self.work_day_type).number_of_days, 2)

    def test_natural_half_day_counts_half(self):
        """
        Dado um tipo 'dia corrido (meio dia)' e um pedido de meio periodo
        Quando a folga de uma sexta pela manha e criada
        Entao number_of_days e 0.5
        """
        leave = self._leave(
            self.natural_half_type,
            request_unit_half=True,
            request_date_from_period="am",
            date_from=datetime(2026, 1, 2, 8, 0),
            date_to=datetime(2026, 1, 2, 12, 0),
            request_date_to="2026-01-02",
        )
        self.assertEqual(leave.number_of_days, 0.5)

    def test_batch_half_day_request_counts_half(self):
        """
        Dado uma folga em meio periodo (singleton)
        Quando o lote e calculado a partir dela
        Entao os dias sao 0.5 (e nao 1)
        """
        leave = self._leave(
            self.natural_half_type,
            request_unit_half=True,
            request_date_from_period="am",
            date_from=datetime(2026, 1, 2, 8, 0),
            date_to=datetime(2026, 1, 2, 12, 0),
            request_date_to="2026-01-02",
        )
        result = leave.with_context(natural_period=True)._get_number_of_days_batch(
            datetime(2026, 1, 2, 8, 0), datetime(2026, 1, 2, 12, 0), self.employee.ids
        )
        self.assertEqual(result[self.employee.id]["days"], 0.5)
        self.assertGreater(result[self.employee.id]["hours"], 0)
