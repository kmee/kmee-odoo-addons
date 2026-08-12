# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Média de verbas variáveis habituais (RF-18).

Súmula 45 TST / CLT art. 142: horas extras habituais e adicional noturno
integram férias, 13º e as verbas rescisórias pela MÉDIA dos últimos 12
meses (ou dos meses trabalhados, se menos), lida dos holerites MENSAIS
confirmados anteriores. O divisor da hora extra é derivado da jornada do
contrato (RF-26); os testes leem `contract._l10n_br_divisor_horas_mensais()`
em vez de fixar 220, para não depender do calendário padrão do ambiente.
"""
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.tests import tagged

from .common import VacationCommon


@tagged("post_install", "-at_install")
class TestMediaHabitual(VacationCommon):
    """Média de HE/adicional noturno compondo férias, 13º e rescisão."""

    def _mensal_done(self, emp, contract, ano, mes, he_50=0.0):
        """Cria e confirma um holerite mensal (CLT) com HE_50 informado."""
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"Mensal {mes}/{ano}",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": self.structure_clt.id,
                "date_from": date(ano, mes, 1),
                "date_to": date(ano, mes, 1) + relativedelta(day=31),
                "l10n_br_horas_extras_50": he_50,
                "company_id": self.env.company.id,
            }
        )
        payslip.action_payslip_done()
        return payslip

    def _valor_he_50(self, contract, horas):
        """Valor da HE 50% (salário-hora × 1,5 × horas), como as regras calculam."""
        divisor = contract._l10n_br_divisor_horas_mensais()
        return round(contract.wage / divisor * 1.5 * horas, 2)

    def test_media_zero_sem_historico(self):
        """Sem holerites mensais anteriores, a média é zero (compat)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00, date_start=date(2024, 1, 1))
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Férias sem histórico",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": self.structure_ferias.id,
                "date_from": date(2024, 6, 1),
                "date_to": date(2024, 6, 30),
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "FERIAS"), 3000.00)

    def test_media_12_meses_compoe_base_das_ferias(self):
        """Média de HE_50 dos últimos 12 meses soma à base das férias.

        6 meses com 10h de HE_50 e 6 meses com 20h → média mensal = a média
        aritmética dos 12 valores. Férias (30/30 dias) = (salário + média).
        """
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00, date_start=date(2023, 1, 1))
        valores = []
        for mes in range(1, 7):
            self._mensal_done(emp, contract, 2024, mes, he_50=10.0)
            valores.append(self._valor_he_50(contract, 10.0))
        for mes in range(7, 13):
            self._mensal_done(emp, contract, 2024, mes, he_50=20.0)
            valores.append(self._valor_he_50(contract, 20.0))
        media_esperada = round(sum(valores) / len(valores), 2)

        ferias = self.env["hr.payslip"].create(
            {
                "name": "Férias com média",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": self.structure_ferias.id,
                "date_from": date(2025, 1, 1),
                "date_to": date(2025, 1, 30),
                "company_id": self.env.company.id,
            }
        )
        ferias.compute_sheet()
        self.assertAlmostEqualMoney(
            self._get_line_total(ferias, "FERIAS"), 3000.00 + media_esperada
        )

    def test_media_ignora_holerites_nao_confirmados(self):
        """Holerites em rascunho (não confirmados) não entram na média."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00, date_start=date(2024, 1, 1))
        # Holerite mensal em RASCUNHO com HE alto: não deve contar.
        self.env["hr.payslip"].create(
            {
                "name": "Mensal rascunho",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": self.structure_clt.id,
                "date_from": date(2024, 5, 1),
                "date_to": date(2024, 5, 31),
                "l10n_br_horas_extras_50": 100.0,
                "company_id": self.env.company.id,
            }
        )
        ferias = self.env["hr.payslip"].create(
            {
                "name": "Férias sem confirmado",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": self.structure_ferias.id,
                "date_from": date(2024, 6, 1),
                "date_to": date(2024, 6, 30),
                "company_id": self.env.company.id,
            }
        )
        ferias.compute_sheet()
        self.assertAlmostEqualMoney(self._get_line_total(ferias, "FERIAS"), 3000.00)

    def test_media_menos_de_12_meses_usa_meses_trabalhados(self):
        """Contrato com 3 meses de casa: média é feita sobre os 3 meses."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00, date_start=date(2024, 4, 1))
        for mes in (4, 5, 6):
            self._mensal_done(emp, contract, 2024, mes, he_50=10.0)
        media_esperada = self._valor_he_50(contract, 10.0)

        ferias = self.env["hr.payslip"].create(
            {
                "name": "Férias 3 meses",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": self.structure_ferias.id,
                "date_from": date(2024, 7, 1),
                "date_to": date(2024, 7, 30),
                "company_id": self.env.company.id,
            }
        )
        ferias.compute_sheet()
        self.assertAlmostEqualMoney(
            self._get_line_total(ferias, "FERIAS"), 3000.00 + media_esperada
        )

    def test_media_compoe_base_do_13(self):
        """A mesma média soma à base do 13º proporcional/bruto."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00, date_start=date(2023, 1, 1))
        for mes in range(1, 13):
            self._mensal_done(emp, contract, 2024, mes, he_50=10.0)
        media_esperada = self._valor_he_50(contract, 10.0)

        decimo = self.env["hr.payslip"].create(
            {
                "name": "13º com média",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": self.structure_13.id,
                "date_from": date(2025, 1, 1),
                "date_to": date(2025, 1, 31),
                "company_id": self.env.company.id,
            }
        )
        decimo.compute_sheet()
        # avos_13 conta só os meses do ANO CIVIL da referência (date_to):
        # com date_to em janeiro/2025, só janeiro conta (1 avo) — não é o
        # 13º anual cheio (esse seria calculado com referência em 31/12).
        avos = decimo.l10n_br_avos_13
        self.assertGreater(avos, 0)
        self.assertAlmostEqualMoney(
            self._get_line_total(decimo, "DECIMO_TERCEIRO_BRUTO"),
            round((3000.00 + media_esperada) * avos / 12, 2),
        )

    def test_media_compoe_decimo_da_rescisao(self):
        """A média também compõe o 13º proporcional pago na rescisão."""
        emp = self._create_employee("Rescisão com Média")
        contract = self._create_contract(emp, wage=3000.00, date_start=date(2024, 1, 1))
        for mes in range(1, 13):
            self._mensal_done(emp, contract, 2024, mes, he_50=10.0)
        media_esperada = self._valor_he_50(contract, 10.0)

        rescisao = self.env["hr.payslip"].create(
            {
                "name": "Rescisão com média",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": self.structure_rescisao.id,
                "date_from": date(2025, 1, 1),
                "date_to": date(2025, 1, 31),
                "company_id": self.env.company.id,
            }
        )
        rescisao.compute_sheet()
        avos = rescisao.l10n_br_avos_13
        self.assertGreater(avos, 0)
        self.assertAlmostEqualMoney(
            self._get_line_total(rescisao, "DECIMO_RESCISAO"),
            round((3000.00 + media_esperada) * avos / 12, 2),
        )
