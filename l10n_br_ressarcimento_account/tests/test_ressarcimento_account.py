# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Contabilização do Ressarcimento via Folha.

Cobertura:
  - Ressarcimento gera lançamento contábil com D/C corretos
  - Lançamento balanceado (débito = crédito)
  - Sem ressarcimento não gera linha contábil
  - Cancelamento remove lançamento
"""
from datetime import date

from odoo.addons.l10n_br_hr_payroll.tests.common import PayrollCommon


class TestRessarcimentoAccount(PayrollCommon):
    """Testes contábeis do ressarcimento de despesas."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.account_despesas_ress = cls.env["account.account"].create(
            {
                "name": "Despesas com Ressarcimento",
                "code": "6.1.9.01",
                "account_type": "expense",
                "company_id": cls.env.company.id,
            }
        )
        cls.account_ress_pagar = cls.env["account.account"].create(
            {
                "name": "Ressarcimento a Pagar",
                "code": "2.1.9.01",
                "account_type": "liability_current",
                "company_id": cls.env.company.id,
            }
        )
        cls.account_salarios = cls.env["account.account"].create(
            {
                "name": "Despesas com Salários",
                "code": "6.1.1.01.T",
                "account_type": "expense",
                "company_id": cls.env.company.id,
            }
        )
        cls.account_salarios_pagar = cls.env["account.account"].create(
            {
                "name": "Salários a Pagar",
                "code": "2.1.1.01.T",
                "account_type": "liability_current",
                "company_id": cls.env.company.id,
            }
        )

        cls.journal_folha = cls.env["account.journal"].create(
            {
                "name": "Folha - Teste Ressarcimento",
                "code": "FORT",
                "type": "general",
                "default_account_id": cls.account_salarios_pagar.id,
                "company_id": cls.env.company.id,
            }
        )

        # Mapear contas: salário base e NET
        cls.env.ref("l10n_br_hr_payroll.hr_rule_salario_base").write(
            {"account_debit": cls.account_salarios.id}
        )
        cls.env.ref("l10n_br_hr_payroll.hr_rule_net").write(
            {"account_credit": cls.account_salarios_pagar.id}
        )

        # Mapear contas: ressarcimento
        cls.env.ref("l10n_br_ressarcimento.salary_rule_ressarcimento").write(
            {
                "account_debit": cls.account_despesas_ress.id,
                "account_credit": cls.account_ress_pagar.id,
            }
        )

        product_vals = {
            "name": "Despesa Viagem",
            "can_be_expensed": True,
            "type": "service",
        }
        # Enterprise sale module adds NOT NULL sale_line_warn
        if "sale_line_warn" in cls.env["product.template"]._fields:
            product_vals["sale_line_warn"] = "no-message"
        cls.product_expense = cls.env["product.product"].create(product_vals)

    def _create_employee(self, name="Funcionário Teste", tipo_contrato="clt"):
        """Override: add CPF required by l10n_br_hr_validacao_folha."""
        return self.env["hr.employee"].create(
            {
                "name": name,
                "l10n_br_tipo_contrato": tipo_contrato,
                "company_id": self.env.company.id,
                "cnpj_cpf": "529.982.247-25",
            }
        )

    def _create_expense_sheet(self, employee, amount=500.0):
        """Helper: create approved expense sheet for payslip reimbursement."""
        expense = self.env["hr.expense"].create(
            {
                "name": "Despesa Teste",
                "employee_id": employee.id,
                "product_id": self.product_expense.id,
                "unit_amount": amount,
                "payment_mode": "own_account",
            }
        )
        sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Relatório Despesa",
                "employee_id": employee.id,
                "expense_line_ids": [(4, expense.id)],
                "l10n_br_refund_in_payslip": True,
            }
        )
        sheet.action_submit_sheet()
        sheet.approve_expense_sheets()
        return sheet

    def _create_payslip_with_journal(self, employee, contract):
        """Helper: create payslip with journal for accounting."""
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"Holerite - {employee.name}",
                "employee_id": employee.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date(2024, 3, 1),
                "date_to": date(2024, 3, 31),
                "company_id": self.env.company.id,
                "journal_id": self.journal_folha.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    def test_ressarcimento_gera_lancamento_contabil(self):
        """Ressarcimento deve gerar linhas no lançamento contábil."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        self._create_expense_sheet(emp, amount=500.0)
        payslip = self._create_payslip_with_journal(emp, contract)

        # Verificar que RESSARCIMENTO foi calculado
        ress_total = self._get_line_total(payslip, "RESSARCIMENTO")
        self.assertAlmostEqualMoney(ress_total, 500.0)

        payslip.action_payslip_done()
        move = payslip.move_id
        self.assertTrue(move, "Folha confirmada deve gerar lançamento contábil")

        # Verificar linhas do ressarcimento
        linhas_debit = move.line_ids.filtered(
            lambda ln: ln.account_id == self.account_despesas_ress
        )
        linhas_credit = move.line_ids.filtered(
            lambda ln: ln.account_id == self.account_ress_pagar
        )
        self.assertTrue(linhas_debit, "Deve haver débito em despesas ressarcimento")
        self.assertTrue(linhas_credit, "Deve haver crédito em ressarcimento a pagar")
        self.assertAlmostEqualMoney(sum(linhas_debit.mapped("debit")), 500.0)
        self.assertAlmostEqualMoney(sum(linhas_credit.mapped("credit")), 500.0)

    def test_lancamento_balanceado_com_ressarcimento(self):
        """Lançamento deve ser balanceado mesmo com ressarcimento."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        self._create_expense_sheet(emp, amount=350.0)
        payslip = self._create_payslip_with_journal(emp, contract)
        payslip.action_payslip_done()
        move = payslip.move_id

        total_debit = sum(move.line_ids.mapped("debit"))
        total_credit = sum(move.line_ids.mapped("credit"))
        self.assertAlmostEqualMoney(total_debit, total_credit, msg="Lançamento D = C")

    def test_sem_ressarcimento_sem_linha_contabil(self):
        """Sem despesas vinculadas, não deve haver linha de ressarcimento."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip_with_journal(emp, contract)
        payslip.action_payslip_done()
        move = payslip.move_id

        linhas_ress = move.line_ids.filtered(
            lambda ln: ln.account_id == self.account_despesas_ress
        )
        self.assertFalse(
            linhas_ress,
            "Sem ressarcimento, não deve haver linha contábil de ressarcimento",
        )

    def test_cancelar_folha_remove_lancamento_ressarcimento(self):
        """Cancelar folha deve remover lançamento incluindo ressarcimento."""
        self.env["ir.config_parameter"].sudo().set_param(
            "payroll.allow_cancel_payslips", "True"
        )
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        self._create_expense_sheet(emp, amount=200.0)
        payslip = self._create_payslip_with_journal(emp, contract)
        payslip.action_payslip_done()
        self.assertTrue(payslip.move_id)

        payslip.action_payslip_cancel()
        payslip.action_payslip_draft()
        self.assertFalse(payslip.move_id)
