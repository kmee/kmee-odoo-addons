# Copyright 2024 ABGF
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""
TDD: Cálculo do INSS com tabela progressiva 2024.

Cobertura:
  - Cada faixa da tabela progressiva
  - Teto do INSS
  - Salário acima do teto
  - Servidor com RPPS (sem INSS RGPS)
  - Aprendiz (alíquota especial)
  - Cálculo proporcional (admissão no meio do mês)
"""
from datetime import date

from .common import PayrollCommon


class TestINSSProgressivo(PayrollCommon):
    """
    Tabela INSS 2024 (progressiva):
      Faixa 1: até R$ 1.412,00      →  7,5%
      Faixa 2: R$ 1.412,01 – 2.666,68  →  9,0%
      Faixa 3: R$ 2.666,69 – 4.000,03  → 12,0%
      Faixa 4: R$ 4.000,04 – 7.786,02  → 14,0%
      Teto: R$ 908,86
    """

    # ── Faixa 1 ──────────────────────────────────────────────────
    def test_inss_salario_minimo_faixa1(self):
        """Salário mínimo 2024: R$1.412,00 → INSS = R$105,90 (100% na faixa 1)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(
            inss, 105.90, msg="INSS do salário mínimo deve ser R$ 105,90"
        )

    def test_inss_exatamente_no_teto_faixa1(self):
        """R$1.412,00 exato: toda a renda na faixa 1 (7,5%)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        # 1412 * 7.5% = 105.90
        self.assertAlmostEqualMoney(inss, 105.90)

    # ── Faixa 2 ──────────────────────────────────────────────────
    def test_inss_faixa2_parcial(self):
        """R$1.500,00: parte na faixa 1, parte na faixa 2."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=1500.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        # Faixa 1: 1412 * 7.5% = 105.90
        # Faixa 2: (1500 - 1412) * 9% = 88 * 9% = 7.92
        # Total: 113.82
        self.assertAlmostEqualMoney(inss, 113.82)

    def test_inss_teto_faixa2(self):
        """R$2.666,68: exatamente no teto da faixa 2."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=2666.68)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        # Faixa 1: 1412 * 7.5% = 105.90
        # Faixa 2: (2666.68 - 1412) * 9% = 1254.68 * 9% = 112.92
        # Total: 218.82
        self.assertAlmostEqualMoney(inss, 218.82)

    # ── Faixa 3 ──────────────────────────────────────────────────
    def test_inss_faixa3_parcial(self):
        """R$3.000,00: parte em faixas 1, 2 e 3."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        # Faixa 1: 1412.00 * 7.5%  = 105.90
        # Faixa 2: 1254.68 * 9.0%  = 112.92
        # Faixa 3: (3000 - 2666.68) * 12% = 333.32 * 12% = 39.998 ≈ 40.00
        # Total: 258.82
        self.assertAlmostEqualMoney(inss, 258.82)

    # ── Faixa 4 ──────────────────────────────────────────────────
    def test_inss_faixa4_parcial(self):
        """R$5.000,00: distribui por todas as 4 faixas."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        # Faixa 1: 1412.00 * 7.5%  = 105.90
        # Faixa 2: 1254.68 * 9.0%  = 112.92
        # Faixa 3: 1333.35 * 12.0% = 160.00
        # Faixa 4: (5000 - 4000.03) * 14% = 999.97 * 14% = 140.00
        # Total: 518.82
        self.assertAlmostEqualMoney(inss, 518.82)

    # ── Teto ──────────────────────────────────────────────────────
    def test_inss_exatamente_no_teto(self):
        """R$7.786,02: teto exato da contribuição INSS 2024 (R$908,86)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=7786.02)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(
            inss, 908.86, msg="No teto do salário, INSS deve ser exatamente R$ 908,86"
        )

    def test_inss_acima_do_teto_10000(self):
        """R$10.000,00: acima do teto → INSS máximo de R$908,86."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=10000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(
            inss, 908.86, msg="Acima do teto salarial, INSS não pode exceder R$ 908,86"
        )

    def test_inss_muito_acima_do_teto(self):
        """R$50.000,00: altíssimo salário → INSS ainda limitado a R$908,86."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=50000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(inss, 908.86)

    # ── Regime RPPS ───────────────────────────────────────────────
    def test_inss_servidor_rpps_nao_desconta_rgps(self):
        """Servidor estatutário com RPPS não deve ter desconto de INSS (RGPS)."""
        emp = self._create_employee(
            tipo_contrato="estatutario",
            regime_previdenciario="rpps",
        )
        contract = self._create_contract(
            emp, wage=8000.00, structure=self.structure_estatuto
        )
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertEqual(
            inss, 0.0, msg="Servidor RPPS não deve ter desconto de INSS (RGPS)"
        )

    def test_rpps_tem_contribuicao_previdenciaria_propria(self):
        """Servidor RPPS deve ter linha de contribuição previdenciária RPPS."""
        emp = self._create_employee(
            tipo_contrato="estatutario",
            regime_previdenciario="rpps",
        )
        contract = self._create_contract(
            emp, wage=8000.00, structure=self.structure_estatuto
        )
        payslip = self._create_payslip(emp, contract)
        rpps = self._get_line_total(payslip, "CONTRIB_RPPS")
        self.assertGreater(
            rpps, 0.0, msg="Servidor RPPS deve ter contribuição previdenciária RPPS"
        )

    # ── Aprendiz ─────────────────────────────────────────────────
    def test_inss_aprendiz_aliquota_2_porcento(self):
        """Aprendiz: alíquota de INSS é 2% sobre o salário bruto."""
        emp = self._create_employee(tipo_contrato="aprendiz")
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        # 1412 * 2% = 28.24
        self.assertAlmostEqualMoney(
            inss, 28.24, msg="Aprendiz deve ter alíquota de INSS de 2%"
        )


class TestINSSProporcional(PayrollCommon):
    """Testes de INSS com admissão/demissão no meio do mês."""

    def test_inss_admissao_meio_do_mes(self):
        """Admitido no dia 16/03/2024: salário proporcional 16/31 do mês."""
        emp = self._create_employee()
        contract = self._create_contract(
            emp, wage=6000.00, date_start=date(2024, 3, 16)
        )
        # Folha do mês de admissão
        payslip = self._create_payslip(
            emp, contract, date_from=date(2024, 3, 16), date_to=date(2024, 3, 31)
        )
        salario_bruto = self._get_line_total(payslip, "SALARIO_BASE")
        # 6000 * (16/31) ≈ 3096.77
        self.assertAlmostEqualMoney(salario_bruto, 3096.77, places=1)
        # INSS calculado sobre o salário proporcional
        inss = self._get_line_total(payslip, "INSS")
        self.assertGreater(inss, 0.0)
        self.assertLess(inss, 908.86)  # não pode atingir o teto com este proporcional


class TestFGTS(PayrollCommon):
    """Testes do cálculo de FGTS."""

    def test_fgts_clt_8_porcento(self):
        """CLT: FGTS é 8% do salário bruto."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        fgts = self._get_line_total(payslip, "FGTS")
        self.assertAlmostEqualMoney(
            fgts, 400.00, msg="FGTS CLT deve ser 8% do salário bruto"
        )

    def test_fgts_aprendiz_2_porcento(self):
        """Aprendiz: FGTS é 2%."""
        emp = self._create_employee(tipo_contrato="aprendiz")
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        fgts = self._get_line_total(payslip, "FGTS")
        # 1412 * 2% = 28.24
        self.assertAlmostEqualMoney(fgts, 28.24, msg="FGTS de aprendiz deve ser 2%")

    def test_fgts_servidor_rpps_zero(self):
        """Servidor RPPS não tem FGTS."""
        emp = self._create_employee(
            tipo_contrato="estatutario",
            regime_previdenciario="rpps",
        )
        contract = self._create_contract(
            emp, wage=8000.00, structure=self.structure_estatuto
        )
        payslip = self._create_payslip(emp, contract)
        fgts = self._get_line_total(payslip, "FGTS")
        self.assertEqual(fgts, 0.0, msg="Servidor RPPS não deve ter FGTS")

    def test_fgts_inclui_hora_extra_na_base(self):
        """FGTS incide sobre salário base + hora extra."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        # Simula hora extra de R$ 200
        self.env["hr.payslip.line"].create(
            {
                "slip_id": payslip.id,
                "name": "Hora Extra 50%",
                "code": "HE50",
                "category_id": self.env.ref("hr_payroll.GROSS").id,
                "quantity": 1,
                "amount": 200.0,
                "total": 200.0,
            }
        )
        # Recalcula
        payslip.compute_sheet()
        fgts = self._get_line_total(payslip, "FGTS")
        # (3000 + 200) * 8% = 256
        self.assertAlmostEqualMoney(
            fgts, 256.00, msg="FGTS deve incidir sobre salário + hora extra"
        )
