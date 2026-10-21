# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import Form, TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestSaleOfDaysOff(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.employee = cls.env["hr.employee"].create({"name": "Abono Employee"})
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Vacation Abono",
                "requires_allocation": "yes",
                "employee_requests": "no",
                "allocation_validation_type": "officer",
                "hr_holidays_sale_of_days_off": True,
            }
        )
        cls.allocation = cls._allocation(cls.employee, cls.leave_type, 30)

    @classmethod
    def _allocation(cls, employee, leave_type, days):
        allocation = cls.env["hr.leave.allocation"].create(
            {
                "name": "Vacation",
                "holiday_status_id": leave_type.id,
                "holiday_type": "employee",
                "employee_id": employee.id,
                "employee_ids": [(6, 0, employee.ids)],
                "number_of_days": days,
                "date_from": "2020-01-01",
                "date_to": "2099-12-31",
            }
        )
        allocation.action_validate()
        return allocation

    def _abono(self, days, allocation=None):
        allocation = allocation or self.allocation
        return self.env["hr.leave.abono"].create(
            {
                "employee_id": allocation.employee_id.id,
                "holiday_allocation_id": allocation.id,
                "date": "2026-01-10",
                "days_sold": days,
            }
        )

    def test_leave_type_flag_reaches_allocation(self):
        """
        Dado um tipo de folga marcado como 'venda de dias'
        Quando se le a alocacao desse tipo
        Entao hr_holidays_sale_of_days_off da alocacao e verdadeiro
        """
        self.assertTrue(self.allocation.hr_holidays_sale_of_days_off)
        other = self.env["hr.leave.type"].create({"name": "Sem venda"})
        self.assertFalse(other.hr_holidays_sale_of_days_off)

    def test_new_abono_defaults(self):
        """
        Dado um abono recem criado
        Quando nada alem do obrigatorio e informado
        Entao nome padrao 'Abono Pecuniario' e estado rascunho; periodo calculado
        """
        abono = self._abono(5)
        self.assertEqual(abono.name, "Abono Pecuni\u00e1rio")
        self.assertEqual(abono.state, "draft")
        self.assertEqual(abono.holiday_allocation_period, "2020-01-01 - 2099-12-31")

    def test_confirm_sells_days(self):
        """
        Dado uma alocacao de 30 dias
        Quando um abono de 5 dias e confirmado
        Entao fica pago, 5 dias vendidos e o saldo cai para 25
        """
        abono = self._abono(5)
        abono.action_confirm()
        self.assertEqual(abono.state, "paid")
        self.assertEqual(self.allocation.number_of_days_sold, 5)
        self.assertEqual(self.allocation.number_of_days, 25)
        self.assertEqual(self.allocation.days_off_sold_display, "5")

    def test_confirm_allows_selling_up_to_ten_days_keeping_twenty(self):
        """
        Dado uma alocacao de 30 dias (regra: sobrar no minimo 20 dias)
        Quando se vende exatamente 10 dias
        Entao a venda e aceita e sobram 20
        """
        self._abono(10).action_confirm()
        self.assertEqual(self.allocation.number_of_days, 20)

    def test_confirm_blocks_when_less_than_twenty_days_would_remain(self):
        """
        Dado uma alocacao de 30 dias
        Quando se tenta vender 11 dias (sobrariam 19)
        Entao ocorre ValidationError e nada e vendido
        """
        abono = self._abono(11)
        with self.assertRaises(ValidationError):
            abono.action_confirm()
        self.assertEqual(abono.state, "draft")
        self.assertEqual(self.allocation.number_of_days_sold, 0)
        self.assertEqual(self.allocation.number_of_days, 30)

    def test_confirm_blocks_zero_days(self):
        """
        Dado um abono com 0 dias
        Quando e confirmado
        Entao ocorre ValidationError
        """
        with self.assertRaises(ValidationError):
            self._abono(0).action_confirm()

    def test_second_sale_considers_what_was_already_sold(self):
        """
        Dado 8 dias ja vendidos de uma alocacao de 30
        Quando se tenta vender mais 5 (sobrariam 17)
        Entao ocorre ValidationError; vender mais 2 (sobram 20) e aceito
        """
        self._abono(8).action_confirm()
        with self.assertRaises(ValidationError):
            self._abono(5).action_confirm()
        self._abono(2).action_confirm()
        self.assertEqual(self.allocation.number_of_days_sold, 10)
        self.assertEqual(self.allocation.number_of_days, 20)

    def test_onchange_days_sold_blocks_unavailable_quantity(self):
        """
        Dado um abono em edicao na alocacao de 30 dias
        Quando days_sold e 5 ou 0 o onchange passa; com 15 (sobrariam 15) falha
        Entao o onchange levanta ValidationError apenas na quantidade indisponivel
        """
        for days in (5, 0):
            self._abono(days)._onchange_days_sold()
        with self.assertRaises(ValidationError):
            self._abono(15)._onchange_days_sold()

    def test_form_creates_and_confirms_abono(self):
        """
        Dado o formulario de abono
        Quando o usuario preenche e confirma pelo botao
        Entao o abono fica pago
        """
        form = Form(self.env["hr.leave.abono"])
        form.employee_id = self.employee
        form.holiday_allocation_id = self.allocation
        form.date = date(2026, 1, 10)
        form.days_sold = 4
        abono = form.save()
        abono.action_confirm()
        self.assertEqual(abono.state, "paid")
        self.assertEqual(self.allocation.number_of_days, 26)

    def test_unlink_paid_abono_restores_days(self):
        """
        Dado um abono pago de 5 dias
        Quando ele e excluido
        Entao os dias voltam a alocacao (vendidos 0, saldo 30)
        """
        abono = self._abono(5)
        abono.action_confirm()
        abono.unlink()
        self.assertEqual(self.allocation.number_of_days_sold, 0)
        self.assertEqual(self.allocation.number_of_days, 30)

    def test_unlink_draft_abono_keeps_balance(self):
        """
        Dado um abono em rascunho
        Quando ele e excluido
        Entao o saldo da alocacao nao muda
        """
        self._abono(5).unlink()
        self.assertEqual(self.allocation.number_of_days, 30)
        self.assertEqual(self.allocation.number_of_days_sold, 0)

    def test_archive_is_refused_without_touching_balance(self):
        """
        Dado um abono pago de 5 dias (o modelo nao tem o campo active)
        Quando alguem tenta arquiva-lo
        Entao o ORM recusa e os dias vendidos continuam na alocacao
        """
        abono = self._abono(5)
        abono.action_confirm()
        self.assertFalse(abono._active_name)
        # No savepoint here on purpose: a refused archive must not have touched
        # the allocation before failing (the ORM fails on models without active).
        refused = False
        try:
            abono.action_archive()
        except (AssertionError, TypeError):
            refused = True
        self.assertTrue(refused, "an abono has no active field to archive")
        self.assertEqual(self.allocation.number_of_days_sold, 5)
        self.assertEqual(self.allocation.number_of_days, 25)

    def test_only_holidays_officer_can_unlink(self):
        """
        Dado um abono e dois usuarios (interno comum e oficial de ferias)
        Quando cada um tenta excluir
        Entao o comum recebe AccessError e o oficial consegue
        """
        abono = self._abono(5)
        plain = new_test_user(self.env, login="abono_plain", groups="base.group_user")
        officer = new_test_user(
            self.env,
            login="abono_officer",
            groups="base.group_user,hr_holidays.group_hr_holidays_user",
        )
        with self.assertRaises(AccessError):
            abono.with_user(plain).unlink()
        abono.with_user(officer).unlink()
        self.assertFalse(abono.exists())

    def test_employee_action_and_display(self):
        """
        Dado um funcionario com alocacao vigente de 30 dias e 5 vendidos
        Quando se abre a acao de venda e se le o contador
        Entao a acao aponta para o abono do funcionario e o contador mostra 5
        """
        self._abono(5).action_confirm()
        self.assertEqual(self.employee.days_off_sold_display, "5")
        action = self.employee.action_sale_of_days_off()
        self.assertEqual(action["res_model"], "hr.leave.abono")
        self.assertEqual(action["domain"], [("employee_id", "=", self.employee.id)])
        self.assertEqual(
            action["context"]["default_holiday_allocation_id"], self.allocation.id
        )
        self.assertEqual(action["context"]["default_employee_id"], self.employee.id)

    def test_employee_without_allocation_shows_zero(self):
        """
        Dado um funcionario sem alocacao vigente
        Quando o contador e lido
        Entao mostra '0' e a alocacao padrao e vazia
        """
        other = self.env["hr.employee"].create({"name": "Sem alocacao"})
        self.assertEqual(other.days_off_sold_display, "0")
        default = other._get_default_hr_leave_allocation_id()
        self.assertFalse(default["id"])

    def test_fractional_days_sold_display(self):
        """
        Dado 2.5 dias vendidos
        Quando o contador da alocacao e lido
        Entao mostra '2.5' (e '5' quando inteiro)
        """
        self.allocation.number_of_days_sold = 2.5
        self.assertEqual(self.allocation.days_off_sold_display, "2.5")

    def test_allocation_action_filters_by_allocation(self):
        """
        Dado uma alocacao
        Quando se abre a acao de venda a partir dela
        Entao o dominio filtra funcionario e alocacao
        """
        action = self.allocation.action_sale_of_days_off()
        self.assertEqual(action["res_model"], "hr.leave.abono")
        self.assertIn(
            ("holiday_allocation_id", "=", self.allocation.id), action["domain"]
        )
        self.assertEqual(
            action["context"]["default_holiday_allocation_id"], self.allocation.id
        )

    def test_sell_days_moves_balance(self):
        """
        Dado uma alocacao de 30 dias
        Quando sell_days(3) e chamado
        Entao 3 passam de saldo para vendidos
        """
        self.allocation.sell_days(3)
        self.assertEqual(self.allocation.number_of_days_sold, 3)
        self.assertEqual(self.allocation.number_of_days, 27)

    def test_sale_views_are_loadable(self):
        """
        Dado as views herdadas (alocacao, funcionario, tipo)
        Quando o arch e montado
        Entao os campos do modulo aparecem
        """
        alloc_arch = self.env["hr.leave.allocation"].get_view(
            self.env.ref("hr_holidays.hr_leave_allocation_view_form").id, "form"
        )["arch"]
        self.assertIn("days_off_sold_display", alloc_arch)
        type_arch = self.env["hr.leave.type"].get_view(
            self.env.ref("hr_holidays.edit_holiday_status_form").id, "form"
        )["arch"]
        self.assertIn("hr_holidays_sale_of_days_off", type_arch)
