# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPlanNextYear(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.today = fields.Date.today()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Next Year Leave",
                "requires_allocation": "yes",
                "employee_requests": "no",
                "allocation_validation_type": "officer",
            }
        )
        cls.next_year_plan = cls._create_plan("Next year plan", "next_year")
        cls.yearly_plan = cls._create_plan("Yearly lost plan", "yearly")

    @classmethod
    def _create_plan(cls, name, frequency):
        plan = cls.env["hr.leave.accrual.plan"].create({"name": name})
        cls.env["hr.leave.accrual.level"].create(
            {
                "accrual_plan_id": plan.id,
                "start_count": 1,
                "start_type": "day",
                "added_value": 1,
                "frequency": frequency,
                "action_with_unused_accruals": "lost",
            }
        )
        return plan

    def _allocation(self, plan, name="Alloc"):
        employee = self.env["hr.employee"].create({"name": "Emp %s" % name})
        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": name,
                "holiday_status_id": self.leave_type.id,
                "holiday_type": "employee",
                "employee_id": employee.id,
                "employee_ids": [(6, 0, employee.ids)],
                "allocation_type": "accrual",
                "accrual_plan_id": plan.id,
                "date_from": self.today - relativedelta(years=2),
                "number_of_days": 0,
            }
        )
        # saldo acumulado e ultima execucao no ano anterior
        allocation.write(
            {
                "number_of_days": 10,
                "lastcall": self.today - relativedelta(years=1, month=6, day=1),
            }
        )
        return allocation

    def test_next_year_frequency_is_selectable(self):
        """
        Dado um plano de acumulo
        Quando um nivel e criado com a frequencia 'next_year'
        Entao o nivel e aceito (selecao e constraint check_dates relaxada)
        """
        level = self.next_year_plan.level_ids
        self.assertEqual(level.frequency, "next_year")

    def test_next_date_is_one_year_after_last_call(self):
        """
        Dado um nivel com frequencia 'next_year'
        Quando se pede a proxima data a partir de 10/03/2025
        Entao a proxima data e 10/03/2026 (um ano depois)
        """
        level = self.next_year_plan.level_ids
        result = level._get_next_date(fields.Date.to_date("2025-03-10"))
        self.assertEqual(result, fields.Date.to_date("2026-03-10"))

    def test_next_date_other_frequency_is_untouched(self):
        """
        Dado um nivel com frequencia 'yearly' (core)
        Quando se pede a proxima data a partir de 10/03/2025
        Entao o calculo do core e mantido (nao vira +1 ano da data dada)
        """
        level = self.yearly_plan.level_ids
        level.write({"yearly_month": "jan", "yearly_day": 1})
        result = level._get_next_date(fields.Date.to_date("2025-03-10"))
        self.assertEqual(result, fields.Date.to_date("2026-01-01"))

    def test_previous_date_is_the_given_date(self):
        """
        Dado um nivel com frequencia 'next_year'
        Quando se pede a data anterior de 10/03/2025
        Entao a propria data e devolvida (chamada coincide com a data de corte)
        """
        level = self.next_year_plan.level_ids
        result = level._get_previous_date(fields.Date.to_date("2025-03-10"))
        self.assertEqual(result, fields.Date.to_date("2025-03-10"))

    def test_previous_date_other_frequency_is_untouched(self):
        """
        Dado um nivel com frequencia 'yearly' (core)
        Quando se pede a data anterior de 10/03/2025
        Entao o core devolve 01/01/2025
        """
        level = self.yearly_plan.level_ids
        level.write({"yearly_month": "jan", "yearly_day": 1})
        result = level._get_previous_date(fields.Date.to_date("2025-03-10"))
        self.assertEqual(result, fields.Date.to_date("2025-01-01"))

    def test_end_of_year_does_not_expire_next_year_allocation(self):
        """
        Dado uma alocacao com nivel 'next_year' e saldo 10, com acao 'perdido'
        Quando roda o fechamento de ano do acumulo
        Entao o saldo e preservado (o modulo pula a expiracao do ano)
        """
        allocation = self._allocation(self.next_year_plan, "keep")
        allocation._end_of_year_accrual()
        self.assertEqual(allocation.number_of_days, 10)

    def test_end_of_year_expires_regular_allocation(self):
        """
        Dado uma alocacao com nivel 'yearly' e saldo 10, com acao 'perdido'
        Quando roda o fechamento de ano do acumulo
        Entao o saldo cai para o consumido (controle: o core continua valendo)
        """
        allocation = self._allocation(self.yearly_plan, "lose")
        allocation._end_of_year_accrual()
        self.assertEqual(allocation.number_of_days, 0)

    def test_end_of_year_processes_every_allocation_of_the_recordset(self):
        """
        Dado duas alocacoes com nivel 'yearly' e saldo 10 cada
        Quando o fechamento de ano roda sobre as duas de uma vez (como o cron)
        Entao as DUAS perdem o saldo, nao so a primeira
        """
        first = self._allocation(self.yearly_plan, "first")
        second = self._allocation(self.yearly_plan, "second")
        (first | second)._end_of_year_accrual()
        self.assertEqual(first.number_of_days, 0)
        self.assertEqual(second.number_of_days, 0)

    def test_end_of_year_mixed_recordset(self):
        """
        Dado uma alocacao 'next_year' seguida de uma 'yearly'
        Quando o fechamento de ano roda sobre as duas
        Entao a 'next_year' preserva o saldo e a 'yearly' expira
        """
        keep = self._allocation(self.next_year_plan, "mixed keep")
        lose = self._allocation(self.yearly_plan, "mixed lose")
        (keep | lose)._end_of_year_accrual()
        self.assertEqual(keep.number_of_days, 10)
        self.assertEqual(lose.number_of_days, 0)
