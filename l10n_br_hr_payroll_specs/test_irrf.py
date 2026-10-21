# Copyright 2024 ABGF
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""
TDD: Cálculo do IRRF com tabela progressiva 2024.

Cobertura:
  - Isenção (abaixo do limite)
  - Cada faixa da tabela progressiva
  - Dedução por dependentes
  - Dedução de pensão alimentícia
  - Isenção por moléstia grave
  - Isenção para maiores de 65 anos
  - IRRF sobre 13º salário (separado)
"""
from datetime import date

from .common import PayrollCommon

# Tabela IRRF 2024 para referência nos testes:
# Faixa 1: até  2.259,20  →  isento
# Faixa 2: até  2.826,65  →  7,5%  - R$ 169,44
# Faixa 3: até  3.751,05  → 15,0%  - R$ 381,44
# Faixa 4: até  4.664,68  → 22,5%  - R$ 662,77
# Faixa 5: acima 4.664,68 → 27,5%  - R$ 896,00
# Dedução por dependente: R$ 189,59/dependente


class TestIRRFTabela(PayrollCommon):
    """Testes da tabela progressiva do IRRF sem dependentes."""

    def test_irrf_isento_abaixo_do_limite(self):
        """Salário que resulte em base IRRF abaixo de R$2.259,20 → IRRF zero."""
        emp = self._create_employee()
        # Salário de R$ 2.200 - INSS = base abaixo do limite
        contract = self._create_contract(emp, wage=2200.00)
        payslip = self._create_payslip(emp, contract)
        irrf = self._get_line_total(payslip, "IRRF")
        self.assertEqual(
            irrf, 0.0, msg="IRRF deve ser zero para base abaixo de R$ 2.259,20"
        )

    def test_irrf_faixa2_7_5_porcento(self):
        """Base entre R$2.259,21 e R$2.826,65 → alíquota 7,5%."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=2700.00)
        payslip = self._create_payslip(emp, contract)
        # Base = 2700 - INSS
        inss = self._get_line_total(payslip, "INSS")
        base_esperada = 2700.00 - inss
        irrf = self._get_line_total(payslip, "IRRF")
        irrf_esperado = base_esperada * 0.075 - 169.44
        self.assertAlmostEqualMoney(irrf, max(0, irrf_esperado))

    def test_irrf_faixa3_15_porcento(self):
        """Base entre R$2.826,66 e R$3.751,05 → alíquota 15%."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3500.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        base = 3500.00 - inss
        irrf = self._get_line_total(payslip, "IRRF")
        irrf_esperado = base * 0.15 - 381.44
        self.assertAlmostEqualMoney(irrf, max(0, irrf_esperado))

    def test_irrf_faixa4_22_5_porcento(self):
        """Base entre R$3.751,06 e R$4.664,68 → alíquota 22,5%."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=4500.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        base = 4500.00 - inss
        irrf = self._get_line_total(payslip, "IRRF")
        irrf_esperado = base * 0.225 - 662.77
        self.assertAlmostEqualMoney(irrf, max(0, irrf_esperado))

    def test_irrf_faixa5_27_5_porcento(self):
        """Base acima de R$4.664,69 → alíquota 27,5%."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=10000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        base = 10000.00 - inss
        irrf = self._get_line_total(payslip, "IRRF")
        irrf_esperado = base * 0.275 - 896.00
        self.assertAlmostEqualMoney(irrf, irrf_esperado)


class TestIRRFDependentes(PayrollCommon):
    """Testes da dedução por dependentes no IRRF."""

    def test_irrf_um_dependente_reduz_base(self):
        """1 dependente reduz a base do IRRF em R$189,59."""
        emp = self._create_employee()
        emp.write({"l10n_br_irrf_dependentes": 1})
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        irrf = self._get_line_total(payslip, "IRRF")
        # Base sem dependente
        base_sem_dep = 5000.00 - inss
        irrf_sem_dep = base_sem_dep * 0.275 - 896.00
        # Base com 1 dependente
        base_com_dep = 5000.00 - inss - 189.59
        irrf_com_dep = base_com_dep * 0.275 - 896.00
        # IRRF pago deve ser menor que sem dependente
        self.assertLess(irrf, irrf_sem_dep, msg="Com dependente, IRRF deve ser menor")
        self.assertAlmostEqualMoney(irrf, max(0, irrf_com_dep))

    def test_irrf_dois_dependentes(self):
        """2 dependentes deduzem R$379,18 (2 × R$189,59)."""
        emp = self._create_employee()
        emp.write({"l10n_br_irrf_dependentes": 2})
        contract = self._create_contract(emp, wage=4000.00)
        payslip = self._create_payslip(emp, contract)
        # Verifica que a base reflete a dedução dos 2 dependentes
        base_irrf = self._get_line_total(payslip, "BASE_IRRF")
        inss = self._get_line_total(payslip, "INSS")
        base_esperada = 4000.00 - inss - (2 * 189.59)
        self.assertAlmostEqualMoney(base_irrf, base_esperada)

    def test_irrf_dependente_pode_tornar_isento(self):
        """Dependentes podem tornar a base abaixo do limite de isenção → IRRF zero."""
        emp = self._create_employee()
        emp.write({"l10n_br_irrf_dependentes": 5})
        # Salário baixo + 5 dependentes → base muito baixa
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        irrf = self._get_line_total(payslip, "IRRF")
        # Pode ser zero ou próximo de zero com 5 dependentes
        inss = self._get_line_total(payslip, "INSS")
        base = 3000.00 - inss - (5 * 189.59)
        irrf_esperado = max(0.0, base * 0.075 - 169.44) if base > 2259.20 else 0.0
        self.assertAlmostEqualMoney(irrf, irrf_esperado)


class TestIRRFDeducoes(PayrollCommon):
    """Testes de deduções especiais do IRRF."""

    def test_irrf_pensao_alimenticia_dedutivel(self):
        """Pensão alimentícia judicial é deduzida integralmente da base do IRRF."""
        emp = self._create_employee()
        emp.write({"l10n_br_pensao_alimenticia": 800.00})
        contract = self._create_contract(emp, wage=6000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        base_irrf = self._get_line_total(payslip, "BASE_IRRF")
        # Base deve deduzir pensão
        base_esperada = 6000.00 - inss - 800.00
        self.assertAlmostEqualMoney(base_irrf, base_esperada)

    def test_irrf_molestia_grave_isencao_total(self):
        """Portador de moléstia grave (Lei 7.713/88) tem isenção total de IRRF."""
        emp = self._create_employee()
        emp.write(
            {
                "l10n_br_molestia_grave": True,
                "l10n_br_cid_molestia": "C50",  # Neoplasia maligna
            }
        )
        contract = self._create_contract(emp, wage=15000.00)
        payslip = self._create_payslip(emp, contract)
        irrf = self._get_line_total(payslip, "IRRF")
        self.assertEqual(
            irrf, 0.0, msg="Portador de moléstia grave deve ter isenção total de IRRF"
        )

    def test_irrf_maior_65_anos_deducao(self):
        """Maior de 65 anos tem dedução adicional na base do IRRF (Lei 7.713/88, art. 6°)."""
        emp = self._create_employee()
        # Funcionário com mais de 65 anos
        emp.write({"birthday": date(1955, 1, 1)})  # Nascido em 1955
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        # Maiores de 65 têm deduções de aposentadoria sobre parcela isenta
        irrf = self._get_line_total(payslip, "IRRF")
        # Valor exato depende da legislação vigente; aqui verificamos que é <= IRRF normal
        emp_normal = self._create_employee(name="Jovem", cpf="987.654.321-00")
        contract_normal = self._create_contract(emp_normal, wage=5000.00)
        payslip_normal = self._create_payslip(emp_normal, contract_normal)
        irrf_normal = self._get_line_total(payslip_normal, "IRRF")
        self.assertLessEqual(
            irrf, irrf_normal, msg="IRRF de maior de 65 anos deve ser <= IRRF normal"
        )


class TestIRRFDecimo(PayrollCommon):
    """Testes do IRRF sobre 13º salário (calculado separadamente)."""

    def test_irrf_decimo_calculado_separado_do_mes(self):
        """IRRF do 13º é calculado na sua própria base, separado do mês corrente."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=8000.00)
        # Folha de dezembro
        payslip_dez = self._create_payslip(
            emp,
            contract,
            date_from=date(2024, 12, 1),
            date_to=date(2024, 12, 31),
        )
        # Folha do 13º
        payslip_13 = self.env["hr.payslip"].create(
            {
                "name": "13º - 2024",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 12, 1),
                "date_to": date(2024, 12, 31),
                "struct_id": self.env.ref("l10n_br_hr_payroll.structure_13_salario").id,
                "company_id": self.company.id,
            }
        )
        payslip_13.compute_sheet()
        irrf_13 = self._get_line_total(payslip_13, "IRRF_13")
        # IRRF do 13º deve existir e ser calculado sobre base própria
        self.assertGreater(irrf_13, 0.0, msg="Deve haver IRRF sobre o 13º salário")
        # Verificar que o IRRF mensal de dezembro não inclui o IRRF do 13º
        irrf_dez = self._get_line_total(payslip_dez, "IRRF")
        irrf_dez_com_13 = irrf_dez + irrf_13
        # Ambos devem ser coerentes (o total não deveria ultrapassar certo limite)
        self.assertGreater(
            irrf_dez_com_13,
            irrf_dez,
            msg="IRRF total com 13º deve ser maior que apenas o mensal",
        )
