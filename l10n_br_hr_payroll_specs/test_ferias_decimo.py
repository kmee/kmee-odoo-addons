# Copyright 2024 ABGF
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""
TDD: Férias (CLT + Estatuto ABGF) e 13º Salário.

Cobertura:
  - Dias de férias por faltas (tabela CLT art. 130)
  - Cálculo do valor das férias + adicional 1/3
  - Abono pecuniário (venda de 1/3)
  - Férias vencidas (dobro)
  - 13º salário: proporcional, 1ª e 2ª parcelas
  - 13º na rescisão
"""
from datetime import date

from odoo.exceptions import UserError, ValidationError

from .common import PayrollCommon


class TestDiasFeriasParFaltas(PayrollCommon):
    """Tabela CLT art. 130 — Dias de férias por faltas no período aquisitivo."""

    def _set_faltas(self, employee, faltas):
        """Helper: registra faltas não justificadas no período aquisitivo."""
        alloc = self.env["hr.leave.allocation"].create(
            {
                "employee_id": employee.id,
                "holiday_status_id": self.env.ref(
                    "l10n_br_hr_vacation.leave_type_ferias"
                ).id,
                "date_from": date(2023, 3, 1),
                "date_to": date(2024, 2, 29),
            }
        )
        alloc.write({"l10n_br_faltas_periodo_aquisitivo": faltas})
        alloc.action_validate()
        return alloc

    def test_ferias_sem_faltas_30_dias(self):
        """0 a 5 faltas → 30 dias de férias."""
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

    def test_ferias_33_faltas_perde_ferias(self):
        """33 ou mais faltas → perde o direito a férias no período."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        alloc = self._set_faltas(emp, 33)
        self.assertEqual(alloc.number_of_days, 0)


class TestValorFerias(PayrollCommon):
    """Testes do cálculo do valor monetário das férias."""

    def test_ferias_30_dias_com_adicional_um_terco(self):
        """30 dias de férias: valor = salário + 1/3 constitucional."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=6000.00)
        payslip = self._create_payslip(
            emp,
            contract,
            date_from=date(2024, 4, 1),
            date_to=date(2024, 4, 30),
        )
        # Configura como folha de férias
        payslip.write(
            {"struct_id": self.env.ref("l10n_br_hr_vacation.structure_ferias").id}
        )
        payslip.compute_sheet()
        ferias = self._get_line_total(payslip, "FERIAS")
        adicional = self._get_line_total(payslip, "ADICIONAL_FERIAS")
        self.assertAlmostEqualMoney(ferias, 6000.00)
        self.assertAlmostEqualMoney(
            adicional,
            2000.00,
            msg="Adicional de 1/3 deve ser exatamente 1/3 do salário",
        )

    def test_adicional_ferias_exatamente_um_terco(self):
        """O adicional de férias deve ser 1/3 do valor das férias (não do salário)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=4500.00)
        payslip_ferias = self.env["hr.payslip"].create(
            {
                "name": "Férias - Teste",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 7, 1),
                "date_to": date(2024, 7, 30),
                "struct_id": self.env.ref("l10n_br_hr_vacation.structure_ferias").id,
                "company_id": self.company.id,
            }
        )
        payslip_ferias.compute_sheet()
        ferias = self._get_line_total(payslip_ferias, "FERIAS")
        adicional = self._get_line_total(payslip_ferias, "ADICIONAL_FERIAS")
        # Adicional deve ser exatamente 1/3 do valor de férias
        self.assertAlmostEqualMoney(adicional, ferias / 3)

    def test_abono_pecuniario_10_dias(self):
        """Abono pecuniário: venda de 10 dias (1/3 de 30)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=6000.00)
        payslip_ferias = self.env["hr.payslip"].create(
            {
                "name": "Férias com Abono - Teste",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 5, 1),
                "date_to": date(2024, 5, 30),
                "struct_id": self.env.ref("l10n_br_hr_vacation.structure_ferias").id,
                "l10n_br_abono_pecuniario": True,
                "company_id": self.company.id,
            }
        )
        payslip_ferias.compute_sheet()
        ferias_gozadas = payslip_ferias.l10n_br_dias_ferias_gozadas
        abono = self._get_line_total(payslip_ferias, "ABONO_PECUNIARIO")
        self.assertEqual(
            ferias_gozadas, 20, msg="Com abono, deve gozar 20 dias (30 - 10)"
        )
        # Abono: 10 dias × (6000/30) = 2000
        self.assertAlmostEqualMoney(abono, 2000.00)

    def test_ferias_minimo_14_dias(self):
        """Período de férias deve ter no mínimo 14 dias consecutivos."""
        emp = self._create_employee()
        self._create_contract(emp, wage=3000.00)
        leave = self.env["hr.leave"].build(
            {
                "employee_id": emp.id,
                "holiday_status_id": self.env.ref(
                    "l10n_br_hr_vacation.leave_type_ferias"
                ).id,
                "date_from": date(2024, 6, 1),
                "date_to": date(2024, 6, 10),  # 10 dias — abaixo do mínimo
            }
        )
        with self.assertRaises(
            (UserError, ValidationError),
            msg="Deve rejeitar férias com menos de 14 dias",
        ):
            leave.action_validate()


class TestDecimoTerceiro(PayrollCommon):
    """Testes do 13º Salário."""

    def test_primeira_parcela_50_porcento(self):
        """1ª parcela do 13º = 50% do salário bruto, sem INSS/IRRF."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00, date_start=date(2024, 1, 1))
        payslip_13_1 = self.env["hr.payslip"].create(
            {
                "name": "13º Adiantamento - 2024",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 11, 1),
                "date_to": date(2024, 11, 30),
                "struct_id": self.env.ref(
                    "l10n_br_hr_payroll.structure_13_primeira_parcela"
                ).id,
                "company_id": self.company.id,
            }
        )
        payslip_13_1.compute_sheet()
        adiant = self._get_line_total(payslip_13_1, "ADIANTAMENTO_13")
        inss = self._get_line_total(payslip_13_1, "INSS")
        irrf = self._get_line_total(payslip_13_1, "IRRF")
        self.assertAlmostEqualMoney(
            adiant,
            2500.00,
            msg="1ª parcela do 13º deve ser R$ 2.500,00 (50% de R$ 5.000,00)",
        )
        self.assertEqual(inss, 0.0, msg="Não deve haver desconto de INSS na 1ª parcela")
        self.assertEqual(irrf, 0.0, msg="Não deve haver desconto de IRRF na 1ª parcela")

    def _test_decimo_proporcional(
        self, date_start, expected_avos, expected_value, wage=6000.00
    ):
        """Helper para testar 13º proporcional."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=wage, date_start=date_start)
        payslip_13 = self.env["hr.payslip"].create(
            {
                "name": "13º 2024",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 12, 1),
                "date_to": date(2024, 12, 31),
                "struct_id": self.env.ref("l10n_br_hr_payroll.structure_13").id,
                "company_id": self.company.id,
            }
        )
        payslip_13.compute_sheet()
        avos = payslip_13.l10n_br_avos_13
        valor_bruto = self._get_line_total(payslip_13, "DECIMO_TERCEIRO_BRUTO")
        self.assertEqual(avos, expected_avos, msg=f"Avos esperados: {expected_avos}")
        self.assertAlmostEqualMoney(
            valor_bruto,
            expected_value,
            msg=f"Valor esperado do 13º: R$ {expected_value}",
        )

    def test_decimo_12_avos(self):
        """Admitido em jan: 12 avos → 13º integral."""
        self._test_decimo_proporcional(date(2024, 1, 1), 12, 6000.00)

    def test_decimo_6_avos(self):
        """Admitido em jul: 6 avos → 50% do salário."""
        self._test_decimo_proporcional(date(2024, 7, 1), 6, 3000.00)

    def test_decimo_3_avos(self):
        """Admitido em out: 3 avos."""
        self._test_decimo_proporcional(date(2024, 10, 1), 3, 1500.00)

    def test_decimo_1_avo_admitido_16_do_mes(self):
        """Admitido no dia 16: conta 1 avo (15 dias ou mais = conta o mês)."""
        self._test_decimo_proporcional(date(2024, 12, 16), 1, 500.00)

    def test_decimo_zero_avos_admitido_25_do_mes(self):
        """Admitido no dia 25: não conta o mês (menos de 15 dias)."""
        self._test_decimo_proporcional(date(2024, 12, 25), 0, 0.00)

    def test_segunda_parcela_desconta_primeira(self):
        """2ª parcela = 13º integral - 1ª parcela já paga."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00, date_start=date(2024, 1, 1))
        # 2ª parcela (dezembro)
        payslip_13_2 = self.env["hr.payslip"].create(
            {
                "name": "13º 2ª Parcela - 2024",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 12, 1),
                "date_to": date(2024, 12, 31),
                "struct_id": self.env.ref(
                    "l10n_br_hr_payroll.structure_13_segunda_parcela"
                ).id,
                "l10n_br_primeira_parcela_13_paga": 2500.00,
                "company_id": self.company.id,
            }
        )
        payslip_13_2.compute_sheet()
        inss_13 = self._get_line_total(payslip_13_2, "INSS_13")
        irrf_13 = self._get_line_total(payslip_13_2, "IRRF_13")
        liquido = payslip_13_2.l10n_br_liquido_13
        # Líquido = 5000 - INSS_13 - IRRF_13 - 2500 (1ª parcela já paga)
        expected_liquido = 5000.00 - inss_13 - irrf_13 - 2500.00
        self.assertAlmostEqualMoney(liquido, expected_liquido)
        self.assertGreater(inss_13, 0.0, "Deve haver INSS no 13º")
        self.assertGreater(irrf_13, 0.0, "Deve haver IRRF no 13º")

    def test_decimo_na_rescisao_proporcional(self):
        """13º na rescisão = proporcional aos meses trabalhados no ano."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=4800.00, date_start=date(2024, 1, 1))
        # Demissão em setembro (9 meses)
        rescisao = self.env["hr.payslip"].create(
            {
                "name": "Rescisão - set/2024",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 9, 1),
                "date_to": date(2024, 9, 30),
                "struct_id": self.env.ref("l10n_br_hr_payroll.structure_rescisao").id,
                "company_id": self.company.id,
            }
        )
        rescisao.compute_sheet()
        decimo_rescisao = self._get_line_total(rescisao, "DECIMO_RESCISAO")
        # 9/12 × 4800 = 3600
        self.assertAlmostEqualMoney(decimo_rescisao, 3600.00)
