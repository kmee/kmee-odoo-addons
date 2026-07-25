# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes ORM das melhorias do motor base da folha:

  - RF-03: pensão alimentícia descontada do líquido (valor fixo e percentual).
  - RF-15: ``_get_baselocaldict`` extensível (sem NameError entre regras).
  - RF-16: IRRF com desconto simplificado mensal (forma mais favorável).
  - RF-26: divisor de jornada derivado do contrato.
"""
from datetime import date

from odoo.tests.common import TransactionCase

from ..models.salary_rules_br import calc_inss as _calc_inss, calc_irrf as _calc_irrf
from .common import PayrollCommon
from .fixtures import FAIXAS_INSS_2024, FAIXAS_IRRF_2024


def _inss(base):
    return _calc_inss(base, FAIXAS_INSS_2024)


def _irrf(base):
    return _calc_irrf(base, FAIXAS_IRRF_2024)


# Desconto simplificado 2024 = 25% × teto da faixa de isenção (2.259,20).
DESCONTO_SIMPLIFICADO_2024 = round(0.25 * 2259.20, 2)  # 564.80


class TestPensaoLiquido(PayrollCommon):
    """RF-03: pensão desconta do líquido e é coerente na base do IRRF."""

    def test_pensao_fixa_aparece_como_ded_e_reduz_net(self):
        """Pensão fixa: rubrica DED, reduz o NET e a base do IRRF."""
        emp = self._create_employee()
        emp.write({"l10n_br_pensao_alimenticia": 800.00})
        contract = self._create_contract(emp, wage=6000.00)
        payslip = self._create_payslip(emp, contract)

        pensao = self._get_line_total(payslip, "PENSAO_ALIMENTICIA")
        self.assertAlmostEqualMoney(pensao, 800.00)

        # A rubrica pertence à categoria DED.
        linha = payslip.line_ids.filtered(
            lambda line: line.code == "PENSAO_ALIMENTICIA"
        )
        self.assertEqual(linha.category_id.code, "DED")

        inss = self._get_line_total(payslip, "INSS")
        base_irrf = self._get_line_total(payslip, "BASE_IRRF")
        self.assertAlmostEqualMoney(base_irrf, 6000.00 - inss - 800.00)

        # NET = salário - INSS - IRRF - pensão (sem faltas/outros descontos).
        irrf = self._get_line_total(payslip, "IRRF")
        net = self._get_line_total(payslip, "NET")
        self.assertAlmostEqualMoney(net, 6000.00 - inss - irrf - 800.00)

    def test_pensao_percentual_aparece_como_ded_e_reduz_net(self):
        """Pensão em % da remuneração: 30% de R$5.000 = R$1.500."""
        emp = self._create_employee()
        emp.write({"l10n_br_pensao_percentual": 30.0})
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)

        pensao = self._get_line_total(payslip, "PENSAO_ALIMENTICIA")
        self.assertAlmostEqualMoney(pensao, 1500.00)

        inss = self._get_line_total(payslip, "INSS")
        base_irrf = self._get_line_total(payslip, "BASE_IRRF")
        self.assertAlmostEqualMoney(base_irrf, 5000.00 - inss - 1500.00)

        irrf = self._get_line_total(payslip, "IRRF")
        net = self._get_line_total(payslip, "NET")
        self.assertAlmostEqualMoney(net, 5000.00 - inss - irrf - 1500.00)

    def test_pensao_fixo_mais_percentual(self):
        """Fixo + percentual somam: R$500 + 10% de R$5.000 = R$1.000."""
        emp = self._create_employee()
        emp.write(
            {
                "l10n_br_pensao_alimenticia": 500.00,
                "l10n_br_pensao_percentual": 10.0,
            }
        )
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        pensao = self._get_line_total(payslip, "PENSAO_ALIMENTICIA")
        self.assertAlmostEqualMoney(pensao, 1000.00)

    def test_sem_pensao_nao_gera_rubrica(self):
        """Sem pensão configurada, a rubrica não aparece no holerite."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        linhas = payslip.line_ids.filtered(
            lambda line: line.code == "PENSAO_ALIMENTICIA"
        )
        self.assertFalse(linhas)


class TestBaselocaldictExtensivel(PayrollCommon):
    """RF-15: regra pode referenciar código de outra regra não calculada."""

    def test_referencia_code_nao_calculado_nao_levanta_nameerror(self):
        """Regra que soma SALARIO_FAMILIA + HE_50 (ambos condicionais e fora
        da antiga tupla fixa) não deve levantar NameError quando não disparam.
        """
        rule = self.env["hr.salary.rule"].create(
            {
                "name": "Teste RF-15",
                "code": "TEST_RF15",
                "sequence": 210,
                "category_id": self.env.ref(
                    "l10n_br_hr_payroll.hr_salary_rule_category_info"
                ).id,
                "condition_select": "none",
                "amount_select": "code",
                # SALARIO_FAMILIA e HE_50 não estavam na tupla fixa antiga.
                "amount_python_compute": "result = SALARIO_FAMILIA + HE_50",
            }
        )
        self.structure_clt.write({"rule_ids": [(4, rule.id)]})

        emp = self._create_employee()  # sem filhos → SALARIO_FAMILIA não dispara
        contract = self._create_contract(emp, wage=3000.00)
        # Não deve levantar NameError.
        payslip = self._create_payslip(emp, contract)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "TEST_RF15"), 0.0)


class TestIRRFSimplificado(PayrollCommon):
    """RF-16: retenção pela forma mais favorável (dedução legal x simplificado)."""

    def test_simplificado_mais_vantajoso(self):
        """Poucas deduções (sem dependentes): simplificado zera o IRRF.

        wage 2.500, mar/2024. Legal: base = 2500 - INSS → IRRF > 0.
        Simplificado: base = 2500 - 564,80 = 1.935,20 < isenção → IRRF 0.
        """
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=2500.00)
        payslip = self._create_payslip(emp, contract)

        inss = self._get_line_total(payslip, "INSS")
        irrf_legal = _irrf(2500.00 - inss)
        self.assertGreater(irrf_legal, 0.0, "cenário deve ter IRRF legal > 0")

        base_simpl = 2500.00 - DESCONTO_SIMPLIFICADO_2024
        irrf_simpl = _irrf(base_simpl)
        self.assertAlmostEqualMoney(irrf_simpl, 0.0)

        irrf = self._get_line_total(payslip, "IRRF")
        self.assertAlmostEqualMoney(irrf, 0.0)

    def test_deducao_legal_mais_vantajosa(self):
        """Muitos dependentes: dedução legal ganha do simplificado.

        wage 5.000, 3 dependentes, mar/2024.
        """
        emp = self._create_employee()
        emp.write({"l10n_br_irrf_dependentes": 3})
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)

        inss = self._get_line_total(payslip, "INSS")
        base_legal = 5000.00 - inss - 3 * 189.59
        irrf_legal = _irrf(base_legal)
        base_simpl = 5000.00 - DESCONTO_SIMPLIFICADO_2024
        irrf_simpl = _irrf(base_simpl)
        self.assertLess(irrf_legal, irrf_simpl, "legal deve ser menor aqui")

        irrf = self._get_line_total(payslip, "IRRF")
        self.assertAlmostEqualMoney(irrf, irrf_legal)


class TestDivisorJornada(TransactionCase):
    """RF-26: divisor mensal derivado da jornada do contrato."""

    def _calendar(self, horas_semanais):
        """Cria calendário com jornada semanal informada (dias × horas/dia)."""
        return self.env["resource.calendar"].create(
            {
                "name": f"Jornada {horas_semanais}h",
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": f"{dia}",
                            "dayofweek": str(dia),
                            "hour_from": 8.0,
                            "hour_to": 8.0 + horas_semanais / 5.0,
                        },
                    )
                    for dia in range(5)  # seg-sex
                ],
            }
        )

    def _contract(self, calendar):
        emp = self.env["hr.employee"].create({"name": "Divisor Teste"})
        return self.env["hr.contract"].create(
            {
                "name": "Contrato Divisor",
                "employee_id": emp.id,
                "wage": 3000.0,
                "date_start": date(2024, 1, 1),
                "state": "open",
                "resource_calendar_id": calendar.id,
                "struct_id": self.env.ref("l10n_br_hr_payroll.structure_clt").id,
            }
        )

    def test_divisor_44h_e_220(self):
        contract = self._contract(self._calendar(44.0))
        self.assertAlmostEqual(contract._l10n_br_divisor_horas_mensais(), 220.0)

    def test_divisor_40h_e_200(self):
        contract = self._contract(self._calendar(40.0))
        self.assertAlmostEqual(contract._l10n_br_divisor_horas_mensais(), 200.0)

    def test_fallback_calendario_sem_jornada_e_220(self):
        """Calendário sem linhas de presença → divisor padrão de 220."""
        calendar = self.env["resource.calendar"].create(
            {"name": "Sem jornada", "attendance_ids": []}
        )
        contract = self._contract(calendar)
        self.assertAlmostEqual(contract._l10n_br_divisor_horas_mensais(), 220.0)
