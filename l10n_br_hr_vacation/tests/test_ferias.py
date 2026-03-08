# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes ORM: Férias CLT.

Cobertura:
  - Dias de férias por faltas (tabela CLT art. 130)
  - Cálculo do valor das férias + adicional 1/3
  - Abono pecuniário (venda de 1/3)
"""
from datetime import date

from .common import VacationCommon


class TestDiasFeriasParFaltas(VacationCommon):
    """Tabela CLT art. 130 — Dias de férias por faltas no período aquisitivo."""

    def _set_faltas(self, employee, faltas):
        """Helper: registra faltas no período aquisitivo."""
        alloc = self.env["hr.leave.allocation"].create(
            {
                "employee_id": employee.id,
                "holiday_status_id": self.leave_type_ferias.id,
                "date_from": date(2023, 3, 1),
                "date_to": date(2024, 2, 29),
            }
        )
        alloc.write({"l10n_br_faltas_periodo_aquisitivo": faltas})
        alloc.action_validate()
        return alloc

    def test_ferias_sem_faltas_30_dias(self):
        """0 faltas → 30 dias de férias."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 0)
        self.assertEqual(alloc.number_of_days, 30)

    def test_ferias_5_faltas_30_dias(self):
        """5 faltas → ainda 30 dias (limite máximo da faixa 1)."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 5)
        self.assertEqual(alloc.number_of_days, 30)

    def test_ferias_6_faltas_24_dias(self):
        """6 faltas → reduz para 24 dias."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 6)
        self.assertEqual(alloc.number_of_days, 24)

    def test_ferias_14_faltas_24_dias(self):
        """14 faltas → 24 dias (teto da faixa 2)."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 14)
        self.assertEqual(alloc.number_of_days, 24)

    def test_ferias_15_faltas_18_dias(self):
        """15 faltas → 18 dias."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 15)
        self.assertEqual(alloc.number_of_days, 18)

    def test_ferias_23_faltas_18_dias(self):
        """23 faltas → 18 dias (teto da faixa 3)."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 23)
        self.assertEqual(alloc.number_of_days, 18)

    def test_ferias_24_faltas_12_dias(self):
        """24 faltas → 12 dias."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 24)
        self.assertEqual(alloc.number_of_days, 12)

    def test_ferias_32_faltas_12_dias(self):
        """32 faltas → 12 dias (teto da faixa 4)."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 32)
        self.assertEqual(alloc.number_of_days, 12)


class TestValorFerias(VacationCommon):
    """Testes do cálculo do valor monetário das férias."""

    def test_ferias_30_dias_com_adicional_um_terco(self):
        """30 dias de férias: valor = salário + 1/3 constitucional."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=6000.00)
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Férias - Teste",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 4, 1),
                "date_to": date(2024, 4, 30),
                "struct_id": self.structure_ferias.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        ferias = self._get_line_total(payslip, "FERIAS")
        adicional = self._get_line_total(payslip, "ADICIONAL_FERIAS")
        self.assertAlmostEqualMoney(ferias, 6000.00)
        self.assertAlmostEqualMoney(adicional, 2000.00)

    def test_adicional_ferias_exatamente_um_terco(self):
        """O adicional de férias deve ser exatamente 1/3 do valor das férias."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=4500.00)
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Férias - Teste",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 7, 1),
                "date_to": date(2024, 7, 30),
                "struct_id": self.structure_ferias.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        ferias = self._get_line_total(payslip, "FERIAS")
        adicional = self._get_line_total(payslip, "ADICIONAL_FERIAS")
        self.assertAlmostEqualMoney(adicional, ferias / 3)

    def test_abono_pecuniario_10_dias(self):
        """Abono pecuniário: venda de 10 dias (1/3 de 30)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=6000.00)
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Férias com Abono - Teste",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 5, 1),
                "date_to": date(2024, 5, 30),
                "struct_id": self.structure_ferias.id,
                "l10n_br_abono_pecuniario": True,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        ferias_gozadas = payslip.l10n_br_dias_ferias_gozadas
        abono = self._get_line_total(payslip, "ABONO_PECUNIARIO")
        self.assertEqual(ferias_gozadas, 20)
        # Abono: 10 dias × (6000/30) = 2000
        self.assertAlmostEqualMoney(abono, 2000.00)
