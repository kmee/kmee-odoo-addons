# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes ORM: INSS progressivo 2024 e FGTS.

Cobertura:
  - Cada faixa da tabela progressiva
  - Teto do INSS
  - Servidor com RPPS (sem INSS RGPS)
  - Aprendiz (alíquota especial)
  - FGTS CLT 8%, aprendiz 2%, RPPS 0%
"""
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

    def test_inss_salario_minimo_faixa1(self):
        """Salário mínimo 2024: R$1.412,00 → INSS = R$105,90."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(inss, 105.90)

    def test_inss_faixa2_parcial(self):
        """R$1.500,00: 1412×7,5% + 88×9% = 113,82."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=1500.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(inss, 113.82)

    def test_inss_teto_faixa2(self):
        """R$2.666,68: exatamente no teto da faixa 2."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=2666.68)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(inss, 218.82)

    def test_inss_faixa3_parcial(self):
        """R$3.000,00: distribui por faixas 1, 2 e 3."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(inss, 258.82)

    def test_inss_faixa4_parcial(self):
        """R$5.000,00: distribui por todas as 4 faixas."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(inss, 518.82)

    def test_inss_exatamente_no_teto(self):
        """R$7.786,02: teto exato da contribuição INSS 2024 (R$908,86)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=7786.02)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(inss, 908.86)

    def test_inss_acima_do_teto(self):
        """R$10.000,00: acima do teto → INSS máximo de R$908,86."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=10000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(inss, 908.86)

    def test_inss_muito_acima_do_teto(self):
        """R$50.000,00: altíssimo salário → INSS limitado a R$908,86."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=50000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertAlmostEqualMoney(inss, 908.86)


class TestINSSRegimes(PayrollCommon):
    """Testes de INSS por regime (RPPS e Aprendiz)."""

    def test_inss_servidor_rpps_nao_desconta_rgps(self):
        """Servidor estatutário com RPPS não deve ter desconto de INSS."""
        emp = self._create_employee(tipo_contrato="estatutario")
        contract = self._create_contract(
            emp, wage=8000.00, structure=self.structure_estatuto
        )
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        self.assertEqual(inss, 0.0)

    def test_rpps_tem_contribuicao_previdenciaria_propria(self):
        """Servidor RPPS deve ter linha de contribuição RPPS."""
        emp = self._create_employee(tipo_contrato="estatutario")
        contract = self._create_contract(
            emp, wage=8000.00, structure=self.structure_estatuto
        )
        payslip = self._create_payslip(emp, contract)
        rpps = self._get_line_total(payslip, "CONTRIB_RPPS")
        self.assertGreater(rpps, 0.0)

    def test_inss_aprendiz_aliquota_2_porcento(self):
        """Aprendiz: alíquota de INSS é 2% sobre o salário bruto."""
        emp = self._create_employee(tipo_contrato="aprendiz")
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        # 1412 * 2% = 28.24
        self.assertAlmostEqualMoney(inss, 28.24)


class TestFGTS(PayrollCommon):
    """Testes do cálculo de FGTS."""

    def test_fgts_clt_8_porcento(self):
        """CLT: FGTS é 8% do salário bruto."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        fgts = self._get_line_total(payslip, "FGTS")
        self.assertAlmostEqualMoney(fgts, 400.00)

    def test_fgts_aprendiz_2_porcento(self):
        """Aprendiz: FGTS é 2%."""
        emp = self._create_employee(tipo_contrato="aprendiz")
        contract = self._create_contract(emp, wage=1412.00)
        payslip = self._create_payslip(emp, contract)
        fgts = self._get_line_total(payslip, "FGTS")
        # 1412 * 2% = 28.24
        self.assertAlmostEqualMoney(fgts, 28.24)

    def test_fgts_servidor_rpps_zero(self):
        """Servidor RPPS não tem FGTS."""
        emp = self._create_employee(tipo_contrato="estatutario")
        contract = self._create_contract(
            emp, wage=8000.00, structure=self.structure_estatuto
        )
        payslip = self._create_payslip(emp, contract)
        fgts = self._get_line_total(payslip, "FGTS")
        self.assertEqual(fgts, 0.0)
