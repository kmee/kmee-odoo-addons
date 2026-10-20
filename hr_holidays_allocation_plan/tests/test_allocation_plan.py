# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestAllocationPlan(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.today = fields.Date.today()
        cls.company = cls.env.company
        cls.department = cls.env["hr.department"].create({"name": "Plan Dept"})
        cls.tag_a = cls.env["hr.employee.category"].create({"name": "Plan Tag A"})
        cls.tag_b = cls.env["hr.employee.category"].create({"name": "Plan Tag B"})
        cls.emp_1 = cls._employee("Plan Emp 1", tags=cls.tag_a | cls.tag_b)
        cls.emp_2 = cls._employee("Plan Emp 2", tags=cls.tag_a)
        cls.emp_no_contract = cls._employee("Plan Emp NoContract", contract=False)
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Plan Leave",
                "requires_allocation": "yes",
                "employee_requests": "no",
                "allocation_validation_type": "officer",
            }
        )

    @classmethod
    def _employee(cls, name, tags=None, contract=True, years_ago=0):
        employee = cls.env["hr.employee"].create(
            {
                "name": name,
                "company_id": cls.company.id,
                "department_id": cls.department.id,
                "category_ids": [(6, 0, (tags or cls.env["hr.employee.category"]).ids)],
            }
        )
        if contract:
            cls._contract(employee, years_ago=years_ago)
        return employee

    @classmethod
    def _contract(cls, employee, years_ago=0):
        start = cls.today - relativedelta(years=years_ago) + relativedelta(days=10)
        if not years_ago:
            start = cls.today - relativedelta(years=1)
        return cls.env["hr.contract"].create(
            {
                "name": "Contract %s" % employee.name,
                "employee_id": employee.id,
                "wage": 1000.0,
                "date_start": start,
                "state": "open",
            }
        )

    def _plan(self, **vals):
        values = {
            "name": "Plan",
            "holiday_status_id": self.leave_type.id,
            "holiday_type": "department",
            "department_id": self.department.id,
            "allocation_type": "regular",
            "number_of_days": 5,
        }
        values.update(vals)
        return self.env["hr.leave.allocation.plan"].create(values)

    def _allocations(self, plan, employee=None):
        allocations = self.env["hr.leave.allocation"].search(
            [("allocation_plan_id", "=", plan.id)]
        )
        if employee:
            allocations = allocations.filtered(lambda a: a.employee_id == employee)
        return allocations

    # ------------------------------------------------------------------
    # defaults e computes
    # ------------------------------------------------------------------
    def test_defaults(self):
        """
        Dado um plano novo no modo empresa
        Quando e criado
        Entao fica em rascunho, com a empresa corrente e sem departamento
        """
        plan = self._plan(holiday_type="company", department_id=False)
        self.assertEqual(plan.state, "draft")
        self.assertEqual(plan.date_from, self.today)
        self.assertEqual(plan.mode_company_id, self.company)
        self.assertFalse(plan.department_id)
        self.assertFalse(plan.category_id)
        self.assertEqual(plan.validity_period, 1)
        self.assertFalse(plan.auto_run)

    def test_changing_mode_resets_company_department_and_category(self):
        """
        Dado um plano por departamento
        Quando o modo muda para etiqueta e depois para empresa
        Entao a empresa e o departamento acompanham o modo
        """
        plan = self._plan()
        self.assertEqual(plan.department_id, self.department)
        plan.holiday_type = "category"
        self.assertFalse(plan.department_id)
        self.assertFalse(plan.mode_company_id)
        plan.holiday_type = "company"
        self.assertEqual(plan.mode_company_id, self.company)

    def test_accrual_plan_from_another_leave_type_is_dropped(self):
        """
        Dado um plano com plano de acumulo restrito a OUTRO tipo de folga
        Quando o tipo de folga do plano muda
        Entao o plano de acumulo incompativel e removido
        """
        other_type = self.env["hr.leave.type"].create({"name": "Other type"})
        accrual = self.env["hr.leave.accrual.plan"].create(
            {"name": "Accrual", "time_off_type_id": other_type.id}
        )
        plan = self._plan(accrual_plan_id=accrual.id, holiday_status_id=other_type.id)
        self.assertEqual(plan.accrual_plan_id, accrual)
        plan.holiday_status_id = self.leave_type
        self.assertFalse(plan.accrual_plan_id)

    # ------------------------------------------------------------------
    # selecao de funcionarios
    # ------------------------------------------------------------------
    def test_recompute_by_department(self):
        """
        Dado um plano por departamento
        Quando o plano e recalculado
        Entao entram os membros do departamento e o estado vai para 'check'
        """
        plan = self._plan()
        plan.action_recompute_plan()
        self.assertEqual(plan.state, "check")
        self.assertEqual(
            plan.plan_employee_ids,
            self.emp_1 | self.emp_2 | self.emp_no_contract,
        )

    def test_recompute_by_company(self):
        """
        Dado um plano por empresa
        Quando o plano e recalculado
        Entao os funcionarios da empresa entram no plano
        """
        plan = self._plan(holiday_type="company", department_id=False)
        plan.action_recompute_plan()
        self.assertTrue(
            (self.emp_1 | self.emp_2 | self.emp_no_contract) <= plan.plan_employee_ids
        )

    def test_recompute_by_single_tag(self):
        """
        Dado funcionarios com A+B e so A
        Quando o plano 'por etiqueta' B e recalculado
        Entao entra so quem tem B
        """
        plan = self._plan(holiday_type="category", category_id=self.tag_b.id)
        plan.action_recompute_plan()
        self.assertEqual(plan.plan_employee_ids, self.emp_1)

    def test_recompute_by_any_tag(self):
        """
        Dado funcionarios com A+B e so A
        Quando o plano 'qualquer etiqueta (OR)' A,B e recalculado
        Entao entram os dois (sem duplicar)
        """
        plan = self._plan(
            holiday_type="category_or",
            category_ids=[(6, 0, (self.tag_a | self.tag_b).ids)],
        )
        plan.action_recompute_plan()
        self.assertEqual(plan.plan_employee_ids, self.emp_1 | self.emp_2)

    def test_recompute_by_all_tags(self):
        """
        Dado funcionarios com A+B e so A
        Quando o plano 'todas as etiquetas (AND)' A,B e recalculado
        Entao entra so quem tem as duas
        """
        plan = self._plan(
            holiday_type="category_and",
            category_ids=[(6, 0, (self.tag_a | self.tag_b).ids)],
        )
        plan.action_recompute_plan()
        self.assertEqual(plan.plan_employee_ids, self.emp_1)

    def test_recompute_expired_plan_is_cancelled(self):
        """
        Dado um plano cuja data final ja passou
        Quando o plano e recalculado
        Entao ele e cancelado e ninguem entra
        """
        plan = self._plan(date_to=self.today - relativedelta(days=1))
        plan.action_recompute_plan()
        self.assertEqual(plan.state, "cancel")
        self.assertFalse(plan.plan_employee_ids)

    # ------------------------------------------------------------------
    # execucao: regular
    # ------------------------------------------------------------------
    def test_run_regular_creates_validated_allocation_per_employee(self):
        """
        Dado um plano regular de 5 dias com dois funcionarios com contrato
        Quando o plano e executado
        Entao cada um recebe exatamente UMA alocacao validada de 5 dias
        """
        plan = self._plan()
        plan.plan_employee_ids = self.emp_1 | self.emp_2
        plan.action_run_update()
        self.assertEqual(len(self._allocations(plan)), 2)
        for employee in (self.emp_1, self.emp_2):
            allocation = self._allocations(plan, employee)
            self.assertEqual(len(allocation), 1)
            self.assertEqual(allocation.state, "validate")
            self.assertEqual(allocation.number_of_days, 5)
            self.assertEqual(allocation.holiday_status_id, self.leave_type)

    def test_run_regular_skips_employee_without_contract(self):
        """
        Dado um funcionario sem contrato no plano
        Quando o plano e executado
        Entao ele nao recebe alocacao
        """
        plan = self._plan()
        plan.plan_employee_ids = self.emp_1 | self.emp_no_contract
        plan.action_run_update()
        self.assertEqual(self._allocations(plan).employee_id, self.emp_1)

    def test_run_regular_twice_does_not_duplicate(self):
        """
        Dado um plano regular ja executado (o cron roda todo dia)
        Quando e executado de novo
        Entao nao nascem alocacoes duplicadas
        """
        plan = self._plan()
        plan.plan_employee_ids = self.emp_1
        plan.action_run_update()
        plan.action_run_update()
        self.assertEqual(len(self._allocations(plan, self.emp_1)), 1)

    def test_run_moves_check_state_to_running(self):
        """
        Dado um plano recalculado (estado 'check')
        Quando e executado
        Entao o estado passa a 'running'
        """
        plan = self._plan()
        plan.action_recompute_plan()
        plan.action_run_update()
        self.assertEqual(plan.state, "running")

    def test_run_cancelled_plan_does_nothing(self):
        """
        Dado um plano cancelado com funcionarios
        Quando e executado
        Entao nenhuma alocacao e criada
        """
        plan = self._plan()
        plan.plan_employee_ids = self.emp_1
        plan.action_cancel()
        plan.action_run_update()
        self.assertFalse(self._allocations(plan))

    # ------------------------------------------------------------------
    # execucao: recorrente e acumulo
    # ------------------------------------------------------------------
    def test_run_recurrent_creates_one_allocation_per_anniversary(self):
        """
        Dado um contrato iniciado ha 3 anos menos 10 dias e plano recorrente
        Quando o plano e executado (sem alocacao imediata)
        Entao nascem as alocacoes dos aniversarios 1 e 2, cada uma de 1 ano
        """
        employee = self._employee("Recurrent", years_ago=3)
        start = employee.contract_id.date_start
        plan = self._plan(allocation_type="recurrent", number_of_days=30)
        plan.plan_employee_ids = employee
        plan.action_run_update()
        allocations = self._allocations(plan, employee).sorted("date_from")
        self.assertEqual(
            allocations.mapped("date_from"),
            [start + relativedelta(years=1), start + relativedelta(years=2)],
        )
        self.assertEqual(
            allocations[0].date_to,
            start + relativedelta(years=2, days=-1),
        )
        self.assertTrue(all(a.state == "validate" for a in allocations))
        self.assertTrue(all(a.number_of_days == 30 for a in allocations))

    def test_run_recurrent_immediate_includes_contract_start(self):
        """
        Dado o mesmo contrato e plano recorrente com alocacao imediata
        Quando o plano e executado
        Entao tambem nasce a alocacao do inicio do contrato (3 no total)
        """
        employee = self._employee("Recurrent imm", years_ago=3)
        start = employee.contract_id.date_start
        plan = self._plan(
            allocation_type="recurrent", number_of_days=30, immediate_allocation=True
        )
        plan.plan_employee_ids = employee
        plan.action_run_update()
        allocations = self._allocations(plan, employee)
        self.assertEqual(len(allocations), 3)
        self.assertIn(start, allocations.mapped("date_from"))

    def test_run_recurrent_twice_does_not_duplicate(self):
        """
        Dado um plano recorrente ja executado
        Quando e executado novamente
        Entao as mesmas vigencias nao sao recriadas
        """
        employee = self._employee("Recurrent twice", years_ago=3)
        plan = self._plan(allocation_type="recurrent", number_of_days=30)
        plan.plan_employee_ids = employee
        plan.action_run_update()
        plan.action_run_update()
        self.assertEqual(len(self._allocations(plan, employee)), 2)

    def test_run_accrual_creates_accrual_allocation_from_contract_start(self):
        """
        Dado um plano de acumulo com plano de acumulo configurado
        Quando o plano e executado
        Entao nasce uma alocacao 'accrual' desde o inicio do contrato, validada
        """
        accrual = self.env["hr.leave.accrual.plan"].create({"name": "Monthly"})
        self.env["hr.leave.accrual.level"].create(
            {
                "accrual_plan_id": accrual.id,
                "start_count": 1,
                "start_type": "day",
                "added_value": 2,
                "frequency": "monthly",
            }
        )
        plan = self._plan(allocation_type="accrual", accrual_plan_id=accrual.id)
        plan.plan_employee_ids = self.emp_1
        plan.action_run_update()
        allocation = self._allocations(plan, self.emp_1)
        self.assertEqual(len(allocation), 1)
        self.assertEqual(allocation.allocation_type, "accrual")
        self.assertEqual(allocation.accrual_plan_id, accrual)
        self.assertEqual(allocation.date_from, self.emp_1.contract_id.date_start)
        self.assertEqual(allocation.state, "validate")

    def test_run_accrual_twice_does_not_duplicate(self):
        """
        Dado um plano de acumulo ja executado
        Quando e executado de novo (cron diario)
        Entao nao nasce segunda alocacao para o mesmo funcionario
        """
        plan = self._plan(allocation_type="accrual")
        plan.plan_employee_ids = self.emp_1
        plan.action_run_update()
        plan.action_run_update()
        self.assertEqual(len(self._allocations(plan, self.emp_1)), 1)

    # ------------------------------------------------------------------
    # ciclo de vida
    # ------------------------------------------------------------------
    def test_cancel_and_back_to_draft(self):
        """
        Dado um plano em rascunho
        Quando e cancelado e depois volta a rascunho
        Entao os estados seguem cancel -> draft
        """
        plan = self._plan()
        plan.action_cancel()
        self.assertEqual(plan.state, "cancel")
        plan.action_back2draft()
        self.assertEqual(plan.state, "draft")

    def test_back_to_draft_only_acts_on_cancelled_plans(self):
        """
        Dado um plano em rascunho
        Quando action_back2draft e chamada
        Entao nada muda (so planos cancelados voltam)
        """
        plan = self._plan()
        plan.plan_employee_ids = self.emp_1
        plan.action_run_update()
        plan.action_back2draft()
        self.assertEqual(len(self._allocations(plan)), 1)

    def test_back_to_draft_removes_allocations(self):
        """
        Dado um plano executado e depois cancelado
        Quando volta a rascunho
        Entao as alocacoes geradas sao removidas
        """
        plan = self._plan()
        plan.plan_employee_ids = self.emp_1 | self.emp_2
        plan.action_run_update()
        self.assertEqual(len(self._allocations(plan)), 2)
        plan.action_cancel()
        plan.action_back2draft()
        self.assertEqual(plan.state, "draft")
        self.assertFalse(self._allocations(plan))

    def test_refuse_draft_and_confirm_allocations(self):
        """
        Dado um plano com alocacoes validadas
        Quando as alocacoes sao recusadas, voltam a rascunho e sao confirmadas
        Entao passam por refuse -> confirm (na 17.0 alocacao nao tem rascunho:
        voltar a rascunho devolve ao primeiro estado, a aprovar)
        """
        confirm_type = self.env["hr.leave.type"].create(
            {
                "name": "Plan Leave (needs confirm)",
                "requires_allocation": "yes",
                "employee_requests": "yes",
                "allocation_validation_type": "officer",
            }
        )
        plan = self._plan(holiday_status_id=confirm_type.id)
        plan.plan_employee_ids = self.emp_1
        plan.action_run_update()
        allocation = self._allocations(plan, self.emp_1)
        plan.action_allocation_refuse()
        self.assertEqual(allocation.state, "refuse")
        plan.action_allocation_draft()
        self.assertEqual(allocation.state, "confirm")
        allocation.action_refuse()
        plan.action_allocation_confirm()
        self.assertEqual(allocation.state, "confirm")

    def test_cron_runs_running_auto_plans(self):
        """
        Dado um plano 'running' com execucao automatica
        Quando o cron de acumulo (_update_accrual) roda
        Entao o plano e recalculado e executado: alocacoes nascem
        """
        plan = self._plan()
        plan.write({"state": "running", "auto_run": True})
        self.env["hr.leave.allocation"]._update_accrual()
        self.assertEqual(self._allocations(plan).employee_id, self.emp_1 | self.emp_2)

    def test_cron_runs_several_plans_at_once(self):
        """
        Dado dois planos 'running' com execucao automatica (o cron os pega juntos)
        Quando o cron de acumulo roda
        Entao os DOIS planos geram alocacoes
        """
        plan_1 = self._plan(name="Plan 1")
        plan_2 = self._plan(
            name="Plan 2", holiday_type="category", category_id=self.tag_b.id
        )
        (plan_1 | plan_2).write({"state": "running", "auto_run": True})
        self.env["hr.leave.allocation"]._update_accrual()
        self.assertEqual(self._allocations(plan_1).employee_id, self.emp_1 | self.emp_2)
        self.assertEqual(self._allocations(plan_2).employee_id, self.emp_1)

    def test_cron_ignores_plans_without_auto_run(self):
        """
        Dado um plano 'running' sem execucao automatica
        Quando o cron de acumulo roda
        Entao o plano e ignorado
        """
        plan = self._plan()
        plan.write({"state": "running", "auto_run": False})
        self.env["hr.leave.allocation"]._update_accrual()
        self.assertFalse(self._allocations(plan))
        self.assertFalse(plan.plan_employee_ids)

    def test_action_open_record(self):
        """
        Dado uma alocacao
        Quando action_open_record e chamada
        Entao devolve a acao de abrir o proprio registro
        """
        plan = self._plan()
        plan.plan_employee_ids = self.emp_1
        plan.action_run_update()
        allocation = self._allocations(plan, self.emp_1)
        action = allocation.action_open_record()
        self.assertEqual(action["res_model"], "hr.leave.allocation")
        self.assertEqual(action["res_id"], allocation.id)
        self.assertEqual(action["view_mode"], "form")

    # ------------------------------------------------------------------
    # permissoes
    # ------------------------------------------------------------------
    def test_only_holidays_manager_can_manage_plans(self):
        """
        Dado um usuario interno comum e um gerente de ferias
        Quando cada um tenta criar um plano
        Entao o comum recebe AccessError e o gerente cria
        """
        plain = new_test_user(self.env, login="plan_plain", groups="base.group_user")
        manager = new_test_user(
            self.env,
            login="plan_manager",
            groups="base.group_user,hr_holidays.group_hr_holidays_manager",
        )
        vals = {
            "name": "Perm",
            "holiday_status_id": self.leave_type.id,
        }
        with self.assertRaises(AccessError):
            self.env["hr.leave.allocation.plan"].with_user(plain).create(vals)
        plan = self.env["hr.leave.allocation.plan"].with_user(manager).create(vals)
        self.assertTrue(plan)
