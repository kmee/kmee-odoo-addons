# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes ORM: Verbas Salariais.

Cobertura:
  - Hora extra 50% e 100%
  - Adicional noturno (20%) e hora reduzida
  - Periculosidade (30% do salário)
  - Insalubridade (10%, 20%, 40% do salário mínimo)
  - Constraint: não acumular periculosidade + insalubridade
  - Salário família: base = salário de contribuição do mês, cota proporcional
    aos dias trabalhados nos meses de admissão/demissão, fora do GROSS
  - Faltas e DSR
  - FGTS integra hora extra
"""
from datetime import date

from odoo.exceptions import ValidationError

from .common import PayrollCommon


class TestHoraExtra(PayrollCommon):
    """Testes de cálculo de hora extra."""

    def test_hora_extra_50_porcento(self):
        """HE em dias úteis: 150% do salário-hora (divisor da jornada)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_horas_extras_50": 10})
        payslip.compute_sheet()
        he = self._get_line_total(payslip, "HE_50")
        # (3000/divisor) × 1.50 × 10, divisor derivado da jornada (RF-26).
        divisor = contract._l10n_br_divisor_horas_mensais()
        self.assertAlmostEqualMoney(he, (3000.00 / divisor) * 1.5 * 10)

    def test_hora_extra_100_porcento(self):
        """HE em domingo/feriado: 200% do salário-hora (divisor da jornada)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_horas_extras_100": 5})
        payslip.compute_sheet()
        he = self._get_line_total(payslip, "HE_100")
        divisor = contract._l10n_br_divisor_horas_mensais()
        self.assertAlmostEqualMoney(he, (3000.00 / divisor) * 2.0 * 5)

    def test_hora_extra_integra_base_fgts(self):
        """Hora extra compõe a base de cálculo do FGTS."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_horas_extras_50": 10})
        payslip.compute_sheet()
        he = self._get_line_total(payslip, "HE_50")
        fgts = self._get_line_total(payslip, "FGTS")
        # FGTS = (3000 + HE) × 8%
        self.assertAlmostEqualMoney(fgts, (3000.00 + he) * 0.08)


class TestFaltasDSR(PayrollCommon):
    """Testes de faltas e desconto de DSR."""

    def test_faltas_desconta_do_salario(self):
        """Faltas injustificadas descontam proporcionalmente."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_faltas_injustificadas": 2})
        payslip.compute_sheet()
        faltas = self._get_line_total(payslip, "FALTAS")
        # (3000 / 30) * 2 = 200.00
        self.assertAlmostEqualMoney(faltas, 200.00)

    def test_dsr_descontado_com_faltas(self):
        """DSR é descontado proporcionalmente às faltas injustificadas."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_faltas_injustificadas": 2})
        payslip.compute_sheet()
        dsr = self._get_line_total(payslip, "DESC_DSR")
        self.assertGreater(dsr, 0.0)


class TestAdicionalNoturno(PayrollCommon):
    """Testes do adicional noturno (art. 73 CLT)."""

    def test_adicional_noturno_20_porcento(self):
        """Adicional noturno = 20% sobre as horas noturnas."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_horas_noturnas": 176})
        payslip.compute_sheet()
        adicional = self._get_line_total(payslip, "ADICIONAL_NOTURNO")
        divisor = contract._l10n_br_divisor_horas_mensais()
        esperado = (3000.00 / divisor) * 0.20 * 176
        self.assertAlmostEqualMoney(adicional, esperado)

    def test_hora_noturna_reduzida_52min30s(self):
        """Hora noturna reduzida (52min30s = 7/8 da hora normal)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write(
            {
                "l10n_br_horas_noturnas": 60,
                "l10n_br_usar_hora_reduzida": True,
            }
        )
        payslip.compute_sheet()
        horas_computadas = payslip.l10n_br_horas_noturnas_computadas
        self.assertAlmostEqualMoney(horas_computadas, 52.5)


class TestPericulosidadeInsalubridade(PayrollCommon):
    """Testes de adicionais de risco."""

    SALARIO_MINIMO_2024 = 1412.00

    def test_periculosidade_30_porcento_do_salario(self):
        """Periculosidade = 30% do salário base."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        contract.write({"l10n_br_periculosidade": True})
        payslip = self._create_payslip(emp, contract)
        adicional = self._get_line_total(payslip, "ADICIONAL_PERICULOSIDADE")
        self.assertAlmostEqualMoney(adicional, 1500.00)

    def test_insalubridade_minimo_10_porcento(self):
        """Insalubridade grau mínimo = 10% do salário mínimo."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        contract.write(
            {
                "l10n_br_insalubridade": True,
                "l10n_br_grau_insalubridade": "minimo",
            }
        )
        payslip = self._create_payslip(emp, contract)
        adicional = self._get_line_total(payslip, "ADICIONAL_INSALUBRIDADE")
        self.assertAlmostEqualMoney(adicional, self.SALARIO_MINIMO_2024 * 0.10)

    def test_insalubridade_medio_20_porcento(self):
        """Insalubridade grau médio = 20% do salário mínimo."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        contract.write(
            {
                "l10n_br_insalubridade": True,
                "l10n_br_grau_insalubridade": "medio",
            }
        )
        payslip = self._create_payslip(emp, contract)
        adicional = self._get_line_total(payslip, "ADICIONAL_INSALUBRIDADE")
        self.assertAlmostEqualMoney(adicional, self.SALARIO_MINIMO_2024 * 0.20)

    def test_insalubridade_maximo_40_porcento(self):
        """Insalubridade grau máximo = 40% do salário mínimo."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        contract.write(
            {
                "l10n_br_insalubridade": True,
                "l10n_br_grau_insalubridade": "maximo",
            }
        )
        payslip = self._create_payslip(emp, contract)
        adicional = self._get_line_total(payslip, "ADICIONAL_INSALUBRIDADE")
        self.assertAlmostEqualMoney(adicional, self.SALARIO_MINIMO_2024 * 0.40)

    def test_periculosidade_e_insalubridade_nao_acumulam(self):
        """Periculosidade e insalubridade não acumulam (Súmula 364 TST)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        with self.assertRaises(ValidationError):
            contract.write(
                {
                    "l10n_br_periculosidade": True,
                    "l10n_br_insalubridade": True,
                    "l10n_br_grau_insalubridade": "maximo",
                }
            )


class TestSalarioFamilia(PayrollCommon):
    """Testes de salário família."""

    def test_salario_familia_faixa1(self):
        """Faixa única 2024 (remuneração até R$1.819,26): R$62,04 por filho."""
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": 1})
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertAlmostEqualMoney(sf, 62.04)

    def test_salario_familia_faixa1_dois_filhos(self):
        """2 filhos na faixa 1: R$124,08 (2 × R$62,04)."""
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": 2})
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertAlmostEqualMoney(sf, 124.08)

    def test_salario_familia_acima_faixa_unica_zero(self):
        """Estrutura de 2 faixas extinta: acima de R$1.819,26 (2024) → zero.

        R$2.000 antes caía na antiga 2ª faixa (R$43,84); hoje não há direito.
        """
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": 1})
        contract = self._create_contract(emp, wage=2000.00)
        payslip = self._create_payslip(emp, contract)
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertAlmostEqualMoney(sf, 0.00)

    def test_salario_familia_acima_teto_zero(self):
        """Salário bem acima do limite: sem salário família."""
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": 3})
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertEqual(sf, 0.0)

    def test_salario_familia_base_e_o_salario_de_contribuicao(self):
        """A base de enquadramento é a REMUNERAÇÃO do mês, não contract.wage.

        Salário de R$1.800 (dentro do limite de R$1.819,26 de 2024) com horas
        extras que levam a remuneração acima do limite → perde a cota. Se a
        regra usasse ``contract.wage`` (bug corrigido), pagaria R$62,04.
        """
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": 1})
        contract = self._create_contract(emp, wage=1800.00)
        payslip = self._create_payslip(emp, contract)
        payslip.write({"l10n_br_horas_extras_50": 10})
        payslip.compute_sheet()
        gross = self._get_line_total(payslip, "GROSS")
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertGreater(gross, 1819.26)
        self.assertEqual(sf, 0.0)

    def test_salario_familia_sem_extras_mantem_cota(self):
        """Contraprova: mesmo salário sem horas extras mantém a cota integral."""
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": 1})
        contract = self._create_contract(emp, wage=1800.00)
        payslip = self._create_payslip(emp, contract)
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "SALARIO_FAMILIA"), 62.04
        )

    def test_salario_familia_fora_da_base_tributavel(self):
        """A cota não integra o salário de contribuição (Lei 8.212/91 art. 28
        §9º "j"): fica fora do GROSS e das bases de INSS/IRRF/FGTS, mas é
        somada ao líquido."""
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": 2})
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        gross = self._get_line_total(payslip, "GROSS")
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        inss = self._get_line_total(payslip, "INSS")
        net = self._get_line_total(payslip, "NET")
        self.assertAlmostEqualMoney(sf, 124.08)
        # GROSS = só o salário: a cota não entrou na base.
        self.assertAlmostEqualMoney(gross, 1412.00)
        self.assertAlmostEqualMoney(inss, 105.90)  # 7,5% de 1412 (tabela 2024)
        # O líquido soma a cota.
        self.assertAlmostEqualMoney(net, 1412.00 + 124.08 - 105.90)

    def test_salario_familia_proporcional_no_mes_de_admissao(self):
        """Mês de admissão: cota proporcional aos dias trabalhados.

        Admitido em 16/03/2024 → 16 dias de vigência no mês →
        R$62,04 × 16/30 = R$33,09.
        """
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": 1})
        contract = self._create_contract(
            emp, wage=1412.00, date_start=date(2024, 3, 16)
        )
        payslip = self._create_payslip(emp, contract)
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertAlmostEqualMoney(sf, 33.09)

    def test_salario_familia_proporcional_no_mes_de_demissao(self):
        """Mês de demissão: cota proporcional aos dias trabalhados.

        Contrato encerrado em 10/03/2024 → 10 dias →
        R$62,04 × 10/30 = R$20,68.
        """
        emp = self._create_employee()
        emp.write({"l10n_br_num_filhos_sf": 1})
        contract = self._create_contract(emp, wage=1412.00)
        contract.write({"date_end": date(2024, 3, 10)})
        payslip = self._create_payslip(emp, contract)
        sf = self._get_line_total(payslip, "SALARIO_FAMILIA")
        self.assertAlmostEqualMoney(sf, 20.68)
