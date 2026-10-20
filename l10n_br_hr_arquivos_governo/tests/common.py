# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class ArquivosGovernoCase(TransactionCase):
    """Empresa, funcionário, contrato e holerites mínimos para os arquivos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.ref("base.main_company")
        cls.company.partner_id.write({"name": "Empresa Teste Ação", "cnpj_cpf": False})
        cls.employee = cls._create_employee("Funcionário Único", "123.456.789-09")
        cls.contract = cls._create_contract(cls.employee, "2024-01-01")
        cls.struct = cls.env["hr.payroll.structure"].create(
            {
                "name": "Estrutura Teste",
                "code": "TST",
            }
        )
        cls.category = cls.env.ref("payroll.BASIC")
        cls.rules = {
            code: cls.env["hr.salary.rule"].create(
                {
                    "name": code,
                    "code": code,
                    "sequence": 1,
                    "category_id": cls.category.id,
                    "amount_select": "fix",
                    "amount_fix": 0.0,
                }
            )
            for code in ("BRUTO", "INSS", "IRRF", "FGTS")
        }
        cls.struct.rule_ids = [(6, 0, [r.id for r in cls.rules.values()])]

    @classmethod
    def _create_employee(cls, name, cpf=None, company=None):
        vals = {"name": name, "company_id": (company or cls.company).id}
        if cpf:
            vals["cnpj_cpf"] = cpf
        return cls.env["hr.employee"].create(vals)

    @classmethod
    def _create_contract(cls, employee, date_start, date_end=False, state="open"):
        return cls.env["hr.contract"].create(
            {
                "name": "Contrato %s" % employee.name,
                "employee_id": employee.id,
                "company_id": employee.company_id.id,
                "wage": 3000.0,
                "date_start": date_start,
                "date_end": date_end,
                "state": state,
            }
        )

    @classmethod
    def _create_payslip(
        cls, date_from, state="done", amounts=None, employee=None, company=None
    ):
        employee = employee or cls.employee
        contract = cls.env["hr.contract"].search(
            [("employee_id", "=", employee.id)], limit=1
        )
        payslip = cls.env["hr.payslip"].create(
            {
                "name": "Holerite %s" % date_from,
                "employee_id": employee.id,
                "contract_id": contract.id,
                "company_id": (company or cls.company).id,
                "struct_id": cls.struct.id,
                "date_from": date_from,
                "date_to": date_from,
            }
        )
        for code, amount in (amounts or {}).items():
            cls.env["hr.payslip.line"].create(
                {
                    "slip_id": payslip.id,
                    "salary_rule_id": cls.rules[code].id,
                    "name": code,
                    "code": code,
                    "category_id": cls.category.id,
                    "contract_id": contract.id,
                    "employee_id": employee.id,
                    "quantity": 1.0,
                    "rate": 100.0,
                    "amount": amount,
                }
            )
        payslip.write({"state": state})
        return payslip
