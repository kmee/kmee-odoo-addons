# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Ressarcimento de Despesas via Folha.

Cobertura:
  - Flag de reembolso via folha na expense sheet
  - Vinculação automática de despesas ao holerite
  - Cálculo do total de ressarcimento
  - Regra salarial informativa
"""
from datetime import date

from odoo.addons.l10n_br_hr_payroll.tests.common import PayrollCommon


class TestRessarcimento(PayrollCommon):
    """Testes do ressarcimento de despesas via folha."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Enterprise sale module may leave sale_line_warn column with NOT NULL
        # even when module is not loaded — set DB default to avoid constraint.
        cls.env.cr.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='product_template' "
            "AND column_name='sale_line_warn' AND is_nullable='NO'"
        )
        if cls.env.cr.fetchone():
            cls.env.cr.execute(
                "ALTER TABLE product_template "
                "ALTER COLUMN sale_line_warn SET DEFAULT 'no-message'"
            )
        product_vals = {
            "name": "Despesa Viagem",
            "can_be_expensed": True,
            "type": "service",
        }
        if "sale_line_warn" in cls.env["product.template"]._fields:
            product_vals["sale_line_warn"] = "no-message"
        cls.product_expense = cls.env["product.product"].create(product_vals)

    def _create_expense_sheet(self, employee, amount=500.0, refund_in_payslip=True):
        """Helper: create approved expense sheet."""
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
                "name": "Relatório Despesa Teste",
                "employee_id": employee.id,
                "expense_line_ids": [(4, expense.id)],
                "l10n_br_refund_in_payslip": refund_in_payslip,
            }
        )
        # Approve the sheet
        sheet.action_submit_sheet()
        sheet.approve_expense_sheets()
        return sheet

    def test_expense_sheet_refund_flag(self):
        """Flag de reembolso via folha é salva."""
        emp = self._create_employee()
        sheet = self._create_expense_sheet(emp, refund_in_payslip=True)
        self.assertTrue(sheet.l10n_br_refund_in_payslip)

    def test_expense_linked_to_payslip(self):
        """Despesas aprovadas são vinculadas ao holerite."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        sheet = self._create_expense_sheet(emp, amount=500.0)
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Holerite Test",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date(2024, 3, 1),
                "date_to": date(2024, 3, 31),
            }
        )
        payslip.compute_sheet()
        self.assertEqual(sheet.l10n_br_payslip_id, payslip)
        self.assertEqual(payslip.l10n_br_expenses_count, 1)

    def test_total_ressarcimento_computed(self):
        """Total de ressarcimento é calculado corretamente."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        sheet1 = self._create_expense_sheet(emp, amount=300.0)
        sheet2 = self._create_expense_sheet(emp, amount=200.0)
        # Verify both sheets are approved and flagged
        self.assertEqual(sheet1.state, "approve")
        self.assertEqual(sheet2.state, "approve")
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Holerite Test",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date(2024, 3, 1),
                "date_to": date(2024, 3, 31),
            }
        )
        payslip.compute_sheet()
        # After compute, sheets should be linked
        self.assertEqual(payslip.l10n_br_expenses_count, 2)
        self.assertAlmostEqual(payslip.l10n_br_total_ressarcimento, 500.0, places=2)

    def test_no_refund_flag_not_linked(self):
        """Despesas sem flag de reembolso não são vinculadas."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        self._create_expense_sheet(emp, amount=500.0, refund_in_payslip=False)
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Holerite Test",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date(2024, 3, 1),
                "date_to": date(2024, 3, 31),
            }
        )
        payslip.compute_sheet()
        self.assertEqual(payslip.l10n_br_expenses_count, 0)
        self.assertAlmostEqual(payslip.l10n_br_total_ressarcimento, 0.0, places=2)

    def test_already_linked_not_duplicated(self):
        """Despesas já vinculadas não são duplicadas."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        sheet = self._create_expense_sheet(emp, amount=500.0)
        payslip1 = self.env["hr.payslip"].create(
            {
                "name": "Holerite 1",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date(2024, 3, 1),
                "date_to": date(2024, 3, 31),
            }
        )
        payslip1.compute_sheet()
        self.assertEqual(sheet.l10n_br_payslip_id, payslip1)
        # Create second payslip — already linked sheet should not move
        payslip2 = self.env["hr.payslip"].create(
            {
                "name": "Holerite 2",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date(2024, 4, 1),
                "date_to": date(2024, 4, 30),
            }
        )
        payslip2.compute_sheet()
        self.assertEqual(payslip2.l10n_br_expenses_count, 0)
        self.assertEqual(sheet.l10n_br_payslip_id, payslip1)
