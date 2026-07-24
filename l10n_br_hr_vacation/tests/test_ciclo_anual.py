# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes ORM: Ciclo anual completo.

Cobertura:
  - 11 holerites mensais CLT (exceto jul=férias)
  - Férias com adicional 1/3
  - 13º: 1ª parcela, 2ª parcela
  - Rescisão com 13º proporcional
  - Líquido positivo em todos os tipos
"""
import calendar
from datetime import date

from .common import VacationCommon


class TestCicloAnual(VacationCommon):
    """Teste end-to-end: 12 meses + férias + 13º + rescisão."""

    def setUp(self):
        super().setUp()
        self.emp = self._create_employee("Ciclo Anual")
        self.contract = self._create_contract(
            self.emp, wage=4500.00, date_start=date(2024, 1, 1)
        )

    def test_ciclo_11_meses_mensal(self):
        """11 holerites mensais CLT (exceto jul=férias) computam corretamente."""
        for month in range(1, 13):
            if month == 7:
                continue  # férias
            last_day = calendar.monthrange(2024, month)[1]
            payslip = self._create_payslip(
                self.emp,
                self.contract,
                date_from=date(2024, month, 1),
                date_to=date(2024, month, last_day),
            )
            sal = self._get_line_total(payslip, "SALARIO_BASE")
            self.assertAlmostEqualMoney(sal, 4500.00)
            net = self._get_line_total(payslip, "NET")
            self.assertGreater(net, 0)

    def test_ferias_valor_e_adicional(self):
        """Férias = salário + adicional 1/3."""
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Férias - Ciclo Anual",
                "employee_id": self.emp.id,
                "contract_id": self.contract.id,
                "date_from": date(2024, 7, 1),
                "date_to": date(2024, 7, 30),
                "struct_id": self.structure_ferias.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        ferias = self._get_line_total(payslip, "FERIAS")
        adicional = self._get_line_total(payslip, "ADICIONAL_FERIAS")
        self.assertAlmostEqualMoney(ferias, 4500.00)
        self.assertAlmostEqualMoney(adicional, 1500.00)

    def test_13_primeira_parcela(self):
        """1ª parcela = 50% sem descontos."""
        payslip = self.env["hr.payslip"].create(
            {
                "name": "13º 1ª Parcela - Ciclo Anual",
                "employee_id": self.emp.id,
                "contract_id": self.contract.id,
                "date_from": date(2024, 11, 1),
                "date_to": date(2024, 11, 30),
                "struct_id": self.structure_13_primeira.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        adiantamento = self._get_line_total(payslip, "ADIANTAMENTO_13")
        inss = self._get_line_total(payslip, "INSS")
        irrf = self._get_line_total(payslip, "IRRF")
        self.assertAlmostEqualMoney(adiantamento, 2250.00)
        self.assertEqual(inss, 0.0)
        self.assertEqual(irrf, 0.0)

    def test_13_segunda_parcela(self):
        """2ª parcela = bruto - INSS - IRRF - 1ª parcela."""
        payslip = self.env["hr.payslip"].create(
            {
                "name": "13º 2ª Parcela - Ciclo Anual",
                "employee_id": self.emp.id,
                "contract_id": self.contract.id,
                "date_from": date(2024, 12, 1),
                "date_to": date(2024, 12, 31),
                "struct_id": self.structure_13_segunda.id,
                "l10n_br_primeira_parcela_13_paga": 2250.00,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        inss_13 = self._get_line_total(payslip, "INSS_13")
        irrf_13 = self._get_line_total(payslip, "IRRF_13")
        liquido = payslip.l10n_br_liquido_13
        expected = 4500.00 - inss_13 - irrf_13 - 2250.00
        self.assertAlmostEqualMoney(liquido, expected)

    def test_rescisao_13_proporcional(self):
        """Rescisão set: 13º = 9/12 × salário."""
        emp = self._create_employee("Rescisão Ciclo")
        contract = self._create_contract(emp, wage=4500.00, date_start=date(2024, 1, 1))
        rescisao = self.env["hr.payslip"].create(
            {
                "name": "Rescisão - set/2024",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 9, 1),
                "date_to": date(2024, 9, 30),
                "struct_id": self.structure_rescisao.id,
                "company_id": self.env.company.id,
            }
        )
        rescisao.compute_sheet()
        decimo_rescisao = self._get_line_total(rescisao, "DECIMO_RESCISAO")
        # 9/12 × 4500 = 3375
        self.assertAlmostEqualMoney(decimo_rescisao, 3375.00)

    def test_net_positivo_todos_tipos(self):
        """Líquido deve ser positivo em todos os tipos de holerite."""
        # Mensal
        payslip_mensal = self._create_payslip(
            self.emp,
            self.contract,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
        )
        self.assertGreater(self._get_line_total(payslip_mensal, "NET"), 0)

        # Férias
        payslip_ferias = self.env["hr.payslip"].create(
            {
                "name": "Férias - NET test",
                "employee_id": self.emp.id,
                "contract_id": self.contract.id,
                "date_from": date(2024, 7, 1),
                "date_to": date(2024, 7, 30),
                "struct_id": self.structure_ferias.id,
                "company_id": self.env.company.id,
            }
        )
        payslip_ferias.compute_sheet()
        net_ferias = self._get_line_total(payslip_ferias, "NET")
        self.assertGreater(net_ferias, 0)

        # 13º 1ª parcela
        payslip_13_1 = self.env["hr.payslip"].create(
            {
                "name": "13º 1ª - NET test",
                "employee_id": self.emp.id,
                "contract_id": self.contract.id,
                "date_from": date(2024, 11, 1),
                "date_to": date(2024, 11, 30),
                "struct_id": self.structure_13_primeira.id,
                "company_id": self.env.company.id,
            }
        )
        payslip_13_1.compute_sheet()
        net_13_1 = self._get_line_total(payslip_13_1, "NET")
        self.assertGreater(net_13_1, 0)
