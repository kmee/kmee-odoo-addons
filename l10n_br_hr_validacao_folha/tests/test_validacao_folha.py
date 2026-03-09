# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Validações da Folha de Pagamento BR.

Cobertura:
  - CPF obrigatório para confirmar folha
  - Duplicidade de holerite por período
  - Datas válidas (date_from <= date_to)
  - Linhas obrigatórias antes de confirmar
"""
from datetime import date

from odoo.exceptions import ValidationError

from odoo.addons.l10n_br_hr_payroll.tests.common import PayrollCommon


class TestValidacaoFolha(PayrollCommon):
    """Testes de validação da folha de pagamento brasileira."""

    def _create_payslip_vals(self, emp, contract, name="Test"):
        return {
            "name": name,
            "employee_id": emp.id,
            "contract_id": contract.id,
            "struct_id": contract.struct_id.id,
            "date_from": date(2024, 3, 1),
            "date_to": date(2024, 3, 31),
        }

    def test_cpf_required_for_confirm(self):
        """Empregado sem CPF não pode confirmar holerite."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self.env["hr.payslip"].create(
            self._create_payslip_vals(emp, contract)
        )
        payslip.compute_sheet()
        with self.assertRaises(ValidationError):
            payslip.action_payslip_done()

    def test_cpf_valid_passes_confirm(self):
        """Empregado com CPF válido confirma normalmente."""
        emp = self._create_employee()
        emp.cnpj_cpf = "123.456.789-09"
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self.env["hr.payslip"].create(
            self._create_payslip_vals(emp, contract)
        )
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, "done")

    def test_duplicate_payslip_rejected(self):
        """Dois holerites para mesmo empregado/período/estrutura são rejeitados."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        self.env["hr.payslip"].create(
            self._create_payslip_vals(emp, contract, "Test 1")
        )
        with self.assertRaises(ValidationError):
            self.env["hr.payslip"].create(
                self._create_payslip_vals(emp, contract, "Test 2")
            )

    def test_duplicate_different_struct_allowed(self):
        """Holerites com estruturas diferentes são permitidos."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        struct2 = self.env["hr.payroll.structure"].create(
            {
                "name": "Estrutura Teste 2",
                "code": "TEST2",
            }
        )
        self.env["hr.payslip"].create(
            self._create_payslip_vals(emp, contract, "Test 1")
        )
        payslip2 = self.env["hr.payslip"].create(
            {
                "name": "Test 2",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": struct2.id,
                "date_from": date(2024, 3, 1),
                "date_to": date(2024, 3, 31),
            }
        )
        self.assertTrue(payslip2)

    def test_cancelled_payslip_allows_new(self):
        """Holerite cancelado permite criar novo para mesmo período."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip1 = self.env["hr.payslip"].create(
            self._create_payslip_vals(emp, contract, "Test 1")
        )
        payslip1.action_payslip_cancel()
        payslip2 = self.env["hr.payslip"].create(
            self._create_payslip_vals(emp, contract, "Test 2")
        )
        self.assertTrue(payslip2)

    def test_invalid_dates_rejected(self):
        """Data inicial posterior à final é rejeitada."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        with self.assertRaises(ValidationError):
            self.env["hr.payslip"].create(
                {
                    "name": "Test",
                    "employee_id": emp.id,
                    "contract_id": contract.id,
                    "struct_id": contract.struct_id.id,
                    "date_from": date(2024, 3, 31),
                    "date_to": date(2024, 3, 1),
                }
            )

    def test_confirm_without_lines_rejected(self):
        """Confirmar holerite sem linhas é rejeitado."""
        emp = self._create_employee()
        emp.cnpj_cpf = "123.456.789-09"
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self.env["hr.payslip"].create(
            self._create_payslip_vals(emp, contract)
        )
        with self.assertRaises(ValidationError):
            payslip.action_payslip_done()

    def test_confirm_with_lines_passes(self):
        """Confirmar holerite com linhas computadas funciona."""
        emp = self._create_employee()
        emp.cnpj_cpf = "123.456.789-09"
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self.env["hr.payslip"].create(
            self._create_payslip_vals(emp, contract)
        )
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, "done")
