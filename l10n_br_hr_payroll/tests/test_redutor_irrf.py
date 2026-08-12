# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes do redutor do IRPF na fonte — Lei 15.270/2025, vigente desde 01/01/2026.

Pontos que estes testes travam (cada um já foi erro real de implementação):

  - A tabela progressiva NÃO mudou: a faixa de isenção continua em
    R$ 2.428,80 e as parcelas a deduzir seguem 182,16 / 394,16 / 675,49 /
    908,73. A isenção efetiva até R$ 5.000 vem SÓ do redutor.
  - O redutor entra DEPOIS do imposto apurado (dedução legal × desconto
    simplificado, o mais favorável).
  - A faixa do redutor é definida pelo rendimento tributável BRUTO do mês,
    não pela base de cálculo após deduções.
  - O redutor é limitado ao imposto apurado (nunca há imposto negativo).
  - Acima de R$ 7.350 o corte é seco.
  - Competências anteriores a 01/2026 continuam SEM redutor.
"""
from datetime import date

from odoo.tests import tagged

from odoo.addons.l10n_br_hr_payroll.models.salary_rules_br import (
    calc_irrf_apos_redutor,
    calc_redutor_irrf,
)

from .common import PayrollCommon
from .fixtures import FAIXAS_REDUTOR_2026


@tagged("post_install", "-at_install")
class TestRedutorIrrfPuro(PayrollCommon):
    """Função pura do redutor (sem ORM)."""

    def test_faixa_isencao_redutor_fixo(self):
        """Rendimento até R$ 5.000: redutor de até R$ 312,89."""
        self.assertAlmostEqual(
            calc_redutor_irrf(5000.00, 312.89, FAIXAS_REDUTOR_2026), 312.89, places=2
        )

    def test_redutor_limitado_ao_imposto_apurado(self):
        """O redutor nunca excede o imposto (não gera restituição na folha)."""
        self.assertAlmostEqual(
            calc_redutor_irrf(4500.00, 200.39, FAIXAS_REDUTOR_2026), 200.39, places=2
        )
        self.assertAlmostEqual(
            calc_irrf_apos_redutor(4500.00, 200.39, FAIXAS_REDUTOR_2026), 0.00, places=2
        )

    def test_faixa_decrescente_formula(self):
        """R$ 5.000,01 a R$ 7.350: redutor = 978,62 − 0,133145 × rendimento."""
        # 978,62 − 0,133145 × 6.000 = 978,62 − 798,87 = 179,75
        self.assertAlmostEqual(
            calc_redutor_irrf(6000.00, 564.85, FAIXAS_REDUTOR_2026), 179.75, places=2
        )

    def test_teto_da_faixa_zera_o_redutor(self):
        """Em R$ 7.350 a fórmula converge para zero (continuidade da lei)."""
        self.assertAlmostEqual(
            calc_redutor_irrf(7350.00, 884.13, FAIXAS_REDUTOR_2026), 0.00, places=2
        )

    def test_acima_do_teto_corte_seco(self):
        """Acima de R$ 7.350 não há redutor algum."""
        self.assertEqual(calc_redutor_irrf(7350.01, 900.00, FAIXAS_REDUTOR_2026), 0.0)
        self.assertEqual(calc_redutor_irrf(8000.00, 1037.85, FAIXAS_REDUTOR_2026), 0.0)

    def test_base_do_redutor_e_o_rendimento_bruto(self):
        """A faixa segue o rendimento BRUTO, não a base após deduções.

        Rendimento bruto de R$ 8.000 tem base de cálculo ~R$ 7.078 (após INSS).
        Se a implementação usasse a base, R$ 8.000 ganharia redutor
        indevidamente — o teste prova que não ganha.
        """
        self.assertEqual(calc_redutor_irrf(8000.00, 1037.85, FAIXAS_REDUTOR_2026), 0.0)
        self.assertGreater(
            calc_redutor_irrf(7078.49, 1037.85, FAIXAS_REDUTOR_2026), 0.0
        )

    def test_sem_faixas_sem_redutor(self):
        """Competência sem redutor cadastrado (tabela vazia) → imposto intacto."""
        self.assertEqual(calc_redutor_irrf(4500.00, 200.39, []), 0.0)
        self.assertAlmostEqual(
            calc_irrf_apos_redutor(4500.00, 200.39, []), 200.39, places=2
        )

    def test_imposto_zero_nao_gera_redutor(self):
        self.assertEqual(calc_redutor_irrf(3000.00, 0.0, FAIXAS_REDUTOR_2026), 0.0)


@tagged("post_install", "-at_install")
class TestRedutorIrrfFolha2026(PayrollCommon):
    """Holerite mensal CLT na competência 03/2026 (redutor vigente)."""

    def _irrf_2026(self, wage):
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=wage, date_start=date(2025, 1, 1))
        payslip = self._create_payslip(
            emp, contract, date_from=date(2026, 3, 1), date_to=date(2026, 3, 31)
        )
        return payslip

    def test_tabela_progressiva_nao_foi_reescrita(self):
        """A faixa de isenção da tabela continua R$ 2.428,80 em 2026.

        Guarda contra o erro clássico de "corrigir" a lei reescrevendo a tabela
        como isenta até R$ 5.000.
        """
        faixas = self.env["l10n_br.hr.payroll.irrf.faixa"]._tabela(date(2026, 3, 31))
        tetos = [base_max for base_max, _aliq, _parc in faixas]
        self.assertAlmostEqual(min(tetos), 2428.80, places=2)
        parcelas = sorted(parc for _b, _a, parc in faixas)
        self.assertEqual(
            [round(p, 2) for p in parcelas],
            [0.0, 182.16, 394.16, 675.49, 908.73],
        )

    def test_desconto_simplificado_2026_inalterado(self):
        """25% de R$ 2.428,80 = R$ 607,20, igual a 2025."""
        modelo = self.env["l10n_br.hr.payroll.irrf.faixa"]
        self.assertAlmostEqual(
            modelo._desconto_simplificado(date(2026, 3, 31)), 607.20, places=2
        )
        self.assertAlmostEqual(
            modelo._desconto_simplificado(date(2025, 6, 30)), 607.20, places=2
        )

    def test_3000_isento_pela_propria_tabela(self):
        """R$ 3.000: o desconto simplificado já zera o imposto (sem redutor).

        3.000 − 607,20 = 2.392,80 < 2.428,80 (faixa isenta).
        """
        payslip = self._irrf_2026(3000.00)
        self.assertEqual(self._get_line_total(payslip, "IRRF"), 0.0)

    def test_4500_imposto_zerado_pelo_redutor(self):
        """R$ 4.500: imposto de R$ 200,39 integralmente absorvido pelo redutor.

        INSS = 431,51 → base legal 4.068,49 → 239,92.
        Simplificado: 3.892,80 → 200,39 (mais favorável).
        Redutor da 1ª faixa (até 5.000) = 312,89, limitado ao imposto → 200,39.
        """
        payslip = self._irrf_2026(4500.00)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "INSS"), 431.51)
        self.assertEqual(self._get_line_total(payslip, "IRRF"), 0.0)

    def test_5000_limite_da_isencao_zerado(self):
        """R$ 5.000 (teto da isenção): imposto 312,89 = redutor máximo → zero."""
        payslip = self._irrf_2026(5000.00)
        self.assertEqual(self._get_line_total(payslip, "IRRF"), 0.0)

    def test_6000_redutor_parcial(self):
        """R$ 6.000: imposto 564,85 − redutor 179,75 = R$ 385,10.

        INSS = 641,51 → base legal 5.358,49 → 27,5% − 908,73 = 564,85
        (mais favorável que o simplificado, 574,29).
        Redutor = 978,62 − 0,133145 × 6.000 = 179,75.
        """
        payslip = self._irrf_2026(6000.00)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "INSS"), 641.51)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "IRRF"), 385.10)

    def test_8000_sem_redutor(self):
        """R$ 8.000 (> 7.350): corte seco, imposto integral de R$ 1.037,85.

        INSS = 921,51 → base legal 7.078,49 → 27,5% − 908,73 = 1.037,85.
        """
        payslip = self._irrf_2026(8000.00)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "INSS"), 921.51)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "IRRF"), 1037.85)

    def test_redutor_nao_gera_irrf_negativo(self):
        """O IRRF nunca fica negativo por conta do redutor."""
        for wage in (2000.00, 3000.00, 4500.00, 5000.00, 6000.00, 8000.00):
            payslip = self._irrf_2026(wage)
            self.assertGreaterEqual(
                self._get_line_total(payslip, "IRRF"), 0.0, msg=f"wage={wage}"
            )


@tagged("post_install", "-at_install")
class TestRedutorIrrfCompetenciaAnterior(PayrollCommon):
    """Competências anteriores a 01/2026 NÃO têm redutor."""

    def _irrf(self, wage, ano, mes=6):
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=wage, date_start=date(ano - 1, 1, 1))
        import calendar

        ultimo = calendar.monthrange(ano, mes)[1]
        payslip = self._create_payslip(
            emp,
            contract,
            date_from=date(ano, mes, 1),
            date_to=date(ano, mes, ultimo),
        )
        return payslip

    def test_2025_sem_redutor_comportamento_preservado(self):
        """06/2025, R$ 4.500: IRRF de R$ 200,39 (sem qualquer redutor).

        INSS 2025 = 439,60 → base legal 4.060,40 → 238,10.
        Simplificado: 3.892,80 → 200,39 (mais favorável) e é o valor retido.
        """
        payslip = self._irrf(4500.00, 2025)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "INSS"), 439.60)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "IRRF"), 200.39)

    def test_2025_tabela_de_redutor_vazia(self):
        """A tabela do redutor não existe para 2025 (e não levanta erro)."""
        faixas = self.env["l10n_br.hr.payroll.irrf.redutor"]._tabela(date(2025, 6, 30))
        self.assertEqual(faixas, [])

    def test_2026_tabela_de_redutor_cadastrada(self):
        """A partir de 01/2026 há duas faixas de redutor cadastradas."""
        faixas = self.env["l10n_br.hr.payroll.irrf.redutor"]._tabela(date(2026, 1, 31))
        self.assertEqual(len(faixas), 2)
        self.assertAlmostEqual(faixas[0][0], 5000.00, places=2)
        self.assertAlmostEqual(faixas[0][1], 312.89, places=2)
        self.assertAlmostEqual(faixas[1][0], 7350.00, places=2)
        self.assertAlmostEqual(faixas[1][1], 978.62, places=2)
        self.assertAlmostEqual(faixas[1][2], 0.133145, places=6)

    def test_2024_sem_redutor(self):
        """03/2024 (competência default dos demais testes): sem redutor."""
        faixas = self.env["l10n_br.hr.payroll.irrf.redutor"]._tabela(date(2024, 3, 31))
        self.assertEqual(faixas, [])
