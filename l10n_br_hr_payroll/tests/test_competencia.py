# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes de resolução das tabelas fiscais por competência (RF-01/RF-02).

Provam que a folha usa a tabela vigente na competência do holerite e NÃO
cai silenciosamente em 2024, e que levanta UserError quando não há tabela.
"""
from datetime import date

from odoo.exceptions import UserError

from .common import PayrollCommon


class TestCompetenciaINSS(PayrollCommon):
    """INSS resolve pela competência, não pela tabela de 2024."""

    def test_inss_2025_usa_tabela_2025(self):
        """Competência 2025: salário mínimo 2025 (R$1.518) na 1ª faixa (7,5%).

        INSS(1518, 2025) = 1518 × 7,5% = 113,85.
        Se caísse em 2024, seria 105,90 + (1518-1412)×9% = 115,44.
        """
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=1518.00, date_start=date(2025, 1, 1))
        payslip = self._create_payslip(
            emp, contract, date_from=date(2025, 3, 1), date_to=date(2025, 3, 31)
        )
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(inss, 113.85)
        self.assertNotAlmostEqual(inss, 115.44, places=2)

    def test_inss_2026_usa_tabela_2026(self):
        """Competência 2026: 1ª faixa até R$1.621 (salário mínimo 2026).

        INSS(1621, 2026) = 1621 × 7,5% = 121,575 → 121,57 (ROUND_HALF_UP
        sobre o float 121,5749…). Sob a tabela de 2024 (teto 1ª faixa 1412)
        o valor seria maior — prova a resolução por competência.
        """
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=1621.00, date_start=date(2026, 1, 1))
        payslip = self._create_payslip(
            emp, contract, date_from=date(2026, 3, 1), date_to=date(2026, 3, 31)
        )
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(inss, 121.57)

    def test_competencia_sem_tabela_levanta_usererror(self):
        """Competência sem tabela cadastrada (2010) → UserError, nunca 2024."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00, date_start=date(2010, 1, 1))
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Holerite 2010",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date(2010, 3, 1),
                "date_to": date(2010, 3, 31),
                "company_id": self.env.company.id,
            }
        )
        with self.assertRaises(UserError):
            payslip.compute_sheet()


class TestCompetenciaSalarioMinimo(PayrollCommon):
    """Salário mínimo (insalubridade) resolve pela competência."""

    def test_insalubridade_2025_usa_sm_2025(self):
        """Insalubridade grau mínimo em 2025 = 10% de R$1.518 = R$151,80."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00, date_start=date(2025, 1, 1))
        contract.write(
            {
                "l10n_br_insalubridade": True,
                "l10n_br_grau_insalubridade": "minimo",
            }
        )
        payslip = self._create_payslip(
            emp, contract, date_from=date(2025, 3, 1), date_to=date(2025, 3, 31)
        )
        adicional = self._get_line_total(payslip, "ADICIONAL_INSALUBRIDADE")
        self.assertAlmostEqualMoney(adicional, 151.80)


class TestCompetenciaSalarioFamilia(PayrollCommon):
    """RF-02: salário família com faixa única vigente por competência."""

    def _create_employee_sf(self, num_filhos):
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": num_filhos})
        return emp

    def test_sf_2024_faixa_unica_dentro_do_limite(self):
        """2024: remuneração até R$1.819,26 → cota R$62,04 por filho."""
        emp = self._create_employee_sf(1)
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertAlmostEqualMoney(sf, 62.04)

    def test_sf_2024_acima_do_limite_zero(self):
        """2024: estrutura de 2 faixas extinta. R$2.000 (>R$1.819,26) → zero."""
        emp = self._create_employee_sf(1)
        contract = self._create_contract(emp, wage=2000.00)
        payslip = self._create_payslip(emp, contract)
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertAlmostEqualMoney(sf, 0.00)

    def test_sf_2025_usa_limite_2025(self):
        """2025: limite sobe para R$1.906,04, cota R$65,00.

        R$1.850 tem direito em 2025 (≤1.906,04) mas não teria em 2024
        (>1.819,26) — prova a resolução por competência.
        """
        emp = self._create_employee_sf(1)
        contract = self._create_contract(emp, wage=1850.00, date_start=date(2025, 1, 1))
        payslip = self._create_payslip(
            emp, contract, date_from=date(2025, 3, 1), date_to=date(2025, 3, 31)
        )
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertAlmostEqualMoney(sf, 65.00)
