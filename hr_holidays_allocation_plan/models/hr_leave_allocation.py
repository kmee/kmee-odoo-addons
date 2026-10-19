# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrLeaveAllocation(models.Model):

    _inherit = "hr.leave.allocation"

    allocation_plan_id = fields.Many2one("hr.leave.allocation.plan")

    def action_open_record(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Record Details",
            "view_mode": "form",
            "res_model": self._name,
            "res_id": self.id,
            "target": "current",
        }

    def _update_accrual(self):
        """
        Method called by the cron task in order to increment the number_of_days
        when necessary.
        """
        # Get the current date to determine the start and end of the accrual period
        allocation_ids = self.env["hr.leave.allocation.plan"].search(
            [
                ("state", "=", "running"),
                ("auto_run", "=", True),
            ]
        )
        allocation_ids.action_recompute_plan()
        allocation_ids.action_run_update()
        return super()._update_accrual()


class HrLeaveAllocationPlan(models.Model):
    """
    Descrição
    =========
    Esta classe define o modelo `hr.leave.allocation.plan` no Odoo, que representa
    um plano de alocação de folgas. O modelo inclui campos para descrição, estado,
    datas de início e término, tipo de folga, notas, aprovador, modo de alocação,
    empresa, departamento, categoria de funcionário, plano de acumulação, execução
    automática, funcionários do plano e alocações.

    Como Utilizar
    =============
    - Crie um novo registro de plano de alocação de folgas.
    - Utilize os métodos `action_recompute_plan` para recalcular o plano com base
      no tipo de alocação e `action_run_update` para executar a atualização do plano
      e criar alocações de folgas para os funcionários selecionados.
      selecionados.
    - O estado do plano pode ser alterado entre `draft`, `check`, `running` e `cancel`.

    Contexto
    Este modelo é utilizado em contextos onde é necessário gerenciar planos de alocação
    de folgas para funcionários em uma empresa. Ele permite a criação de planos de folgas
    em massa com base em diferentes critérios, como empresa, departamento ou categoria
    de funcionário. O modelo também suporta a validação automática de alocações e o
    rastreamento de mudanças de estado.
    e o rastreamento de mudanças de estado.
    """

    _name = "hr.leave.allocation.plan"
    _description = "Time Off Allocation Plan"
    _order = "create_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _mail_post_access = "read"

    name = fields.Char("Description")
    active = fields.Boolean(default=True)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("cancel", "Cancelled"),
            ("check", "Check"),
            ("running", "Running"),
        ],
        string="Status",
        readonly=True,
        tracking=True,
        copy=False,
        default="draft",
    )
    date_from = fields.Date(
        "Start Date",
        index=True,
        copy=False,
        default=fields.Date.context_today,
        tracking=True,
        required=True,
    )
    date_to = fields.Date(
        "End Date",
        copy=False,
        tracking=True,
    )
    holiday_status_id = fields.Many2one(
        "hr.leave.type",
        string="Time Off Type",
        required=True,
        readonly=False,
    )
    notes = fields.Text(
        "Reasons",
    )

    approver_id = fields.Many2one(
        "hr.employee",
        string="First Approval",
        readonly=True,
        copy=False,
        help="This area is automatically filled by the user who validates the allocation",
    )

    # mode
    holiday_type = fields.Selection(
        [
            # ('employee', 'By Employee'),
            ("company", "By Company"),
            ("department", "By Department"),
            ("category", "By Employee Tag"),
            ("category_and", "By all Employee Tags (AND)"),
            ("category_or", "By any of Employee Tags (OR)"),
        ],
        string="Allocation Mode",
        required=True,
        default="company",
        help="Allow to create requests in batchs:\n- By Employee: for a specific employee"
        "\n- By Company: all employees of the specified company"
        "\n- By Department: all employees of the specified department"
        "\n- By Employee Tag: all employees of the specific employee group category",
    )

    allocation_type = fields.Selection(
        [
            ("regular", "Regular / Fixed"),
            ("accrual", "Accrual"),
            ("recurrent", "Recurrent Allocation"),
        ],
        required=True,
        default="accrual",
    )

    mode_company_id = fields.Many2one(
        "res.company",
        compute="_compute_from_holiday_type",
        store=True,
        string="Company Mode",
        readonly=False,
    )
    department_id = fields.Many2one(
        "hr.department",
        compute="_compute_department_id",
        store=True,
        string="Department",
        readonly=False,
    )
    category_id = fields.Many2one(
        "hr.employee.category",
        compute="_compute_from_holiday_type",
        store=True,
        string="Employee Tag",
        readonly=False,
    )

    category_ids = fields.Many2many(
        "hr.employee.category",
        string="Employee Tags",
        readonly=False,
    )

    accrual_plan_id = fields.Many2one(
        "hr.leave.accrual.plan",
        compute="_compute_from_holiday_status_id",
        store=True,
        readonly=False,
        domain="""['|',
            ('time_off_type_id', '=', False),
            ('time_off_type_id', '=', holiday_status_id)]""",
        tracking=True,
    )

    auto_run = fields.Boolean(default=False)

    plan_employee_ids = fields.Many2many(
        "hr.employee",
        relation="hr_allocation_employee_rel2",
        column1="allocation_id",
        column2="employee_id",
    )

    allocation_ids = fields.One2many(
        comodel_name="hr.leave.allocation",
        inverse_name="allocation_plan_id",
        readonly=True,
    )

    recurring_renewal_frequency = fields.Integer(
        default=1,
    )

    number_of_days = fields.Float(
        string="Number of Days",
    )

    immediate_allocation = fields.Boolean(
        default=False,
    )

    validity_period = fields.Integer(
        string="Validity Period (years)",
        default=1,
        help="Defines how long the allocated leave is valid from the allocation date.",
    )

    @api.depends("holiday_type")
    def _compute_from_holiday_type(self):
        for plan in self:
            if plan.holiday_type == "company":
                plan.mode_company_id = plan.mode_company_id or self.env.company
                plan.category_id = False
            elif plan.holiday_type == "category":
                plan.mode_company_id = False
            else:
                plan.mode_company_id = False
                plan.category_id = False

    @api.depends("holiday_type")
    def _compute_department_id(self):
        for plan in self:
            if plan.holiday_type != "department":
                plan.department_id = False

    @api.depends("holiday_status_id")
    def _compute_from_holiday_status_id(self):
        for plan in self:
            accrual_type = plan.accrual_plan_id.time_off_type_id
            if accrual_type and accrual_type != plan.holiday_status_id:
                plan.accrual_plan_id = False

    def action_recompute_plan(self):
        for record in self:
            employees = self.env["hr.employee"]

            if record.date_to and record.date_to < fields.Date.today():
                record.state = "cancel"
                continue

            if record.state == "draft":
                record.state = "check"
            if record.holiday_type == "employee":
                employees = record.employee_ids
            elif record.holiday_type == "category_and":
                employees = record.env["hr.employee"].search([])
                for category in record.category_ids:
                    employees = employees.filtered(lambda e: category in e.category_ids)
            elif record.holiday_type == "category_or":
                for category_id in record.category_ids:
                    employees |= category_id.employee_ids
            elif record.holiday_type == "category":
                employees = record.category_id.employee_ids
            elif record.holiday_type == "department":
                employees = record.department_id.member_ids
            else:
                employees = record.env["hr.employee"].search(
                    [("company_id", "=", record.mode_company_id.id)]
                )
            record._recompute_plans(employees)

    def _recompute_plans(self, employees):
        self.plan_employee_ids |= employees

    def _get_running_contracts(self, employee):
        running_contracts = (
            self.env["hr.contract"]
            .search(
                [
                    ("employee_id", "=", employee.id),
                    ("state", "in", ("open", "close")),
                ],
            )
            .mapped("date_start")
        )
        return running_contracts

    def _create_recurrent(self, employee, running_contracts):
        oldest_running_contract = min(running_contracts)
        current_date = (
            oldest_running_contract  # Start allocation from contract start date
        )
        jump = False

        while current_date < fields.Date.today():

            if not self.immediate_allocation and not jump:
                current_date += relativedelta(years=self.recurring_renewal_frequency)
                jump = True

            date_from = current_date
            date_to = date_from + relativedelta(years=self.validity_period, days=-1)

            if not self.env["hr.leave.allocation"].search_count(
                [
                    ("employee_id", "=", employee.id),
                    ("date_from", "<=", date_to),
                    ("date_to", ">=", date_from),
                    ("allocation_plan_id", "=", self.id),
                ]
            ):
                allocation = self.env["hr.leave.allocation"].create(
                    {
                        "name": self.name,
                        "holiday_status_id": self.holiday_status_id.id,
                        "notes": self.notes,
                        "number_of_days": self.number_of_days,
                        "employee_id": employee.id,
                        "state": "confirm",
                        "allocation_type": "regular",
                        "date_from": date_from,
                        "date_to": date_to,
                        "accrual_plan_id": self.accrual_plan_id.id,
                        "allocation_plan_id": self.id,
                    }
                )
                allocation.action_validate()

            # Increment to the next year after the first allocation
            current_date += relativedelta(years=1)

    def _has_allocation(self, employee):
        """Allocation already generated by this plan for the employee."""
        return bool(
            self.env["hr.leave.allocation"].search_count(
                [
                    ("employee_id", "=", employee.id),
                    ("allocation_plan_id", "=", self.id),
                ]
            )
        )

    def _create_regular(self, employee):
        """Aloca somente uma vez de forma fixa"""
        if self._has_allocation(employee):
            return
        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": self.name,
                "holiday_status_id": self.holiday_status_id.id,
                "notes": self.notes,
                "number_of_days": self.number_of_days,
                "employee_id": employee.id,
                "state": "confirm",
                "allocation_type": "regular",
                "date_from": self.date_from,
                "date_to": self.date_to,
                "accrual_plan_id": self.accrual_plan_id.id,
                "allocation_plan_id": self.id,
            }
        )
        allocation.action_validate()

    def _create_accrual(self, employee, running_contracts):
        """
        Cria alocações de folga conforme o plano de acumulação definido.
        Este método cria uma alocação que é válida até o final do período definido.
        """
        if self._has_allocation(employee):
            return
        oldest_running_contract = min(running_contracts)
        date_from = oldest_running_contract
        date_to = self.date_to

        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": self.name,
                "holiday_status_id": self.holiday_status_id.id,
                "notes": self.notes,
                "number_of_days": self.number_of_days,
                "employee_id": employee.id,
                "state": "confirm",
                "allocation_type": "accrual",
                "date_from": date_from,
                "date_to": date_to,
                "accrual_plan_id": self.accrual_plan_id.id,
                "allocation_plan_id": self.id,
            }
        )
        allocation.action_validate()

    def action_run_update(self):
        for record in self:
            if record.state == "check":
                record.state = "running"

            if record.state == "cancel":
                continue

            for employee in record.plan_employee_ids:
                running_contracts = record._get_running_contracts(employee)
                if not running_contracts:
                    continue

                if record.allocation_type == "recurrent":
                    record._create_recurrent(
                        employee=employee, running_contracts=running_contracts
                    )
                elif record.allocation_type == "regular":
                    record._create_regular(employee=employee)
                elif record.allocation_type == "accrual":
                    record._create_accrual(
                        employee=employee, running_contracts=running_contracts
                    )

    def action_cancel(self):
        for record in self:
            record.state = "cancel"

    def action_back2draft(self):
        for record in self:
            if record.state == "cancel":
                record.state = "draft"
                record.action_allocation_refuse()
                record.action_allocation_draft()
                record.action_allocation_unlink()

    def action_allocation_refuse(self):
        for record in self:
            record.allocation_ids.action_refuse()

    def action_allocation_draft(self):
        """In 17.0 allocations have no draft state, so refused ones go back to
        the first state (to approve)."""
        for record in self:
            record.allocation_ids.filtered(lambda a: a.state == "refuse").write(
                {"state": "confirm"}
            )

    def action_allocation_unlink(self):
        for record in self:
            record.allocation_ids.unlink()

    def action_allocation_confirm(self):
        for record in self:
            record.allocation_ids.filtered(lambda a: a.state == "refuse").write(
                {"state": "confirm"}
            )
