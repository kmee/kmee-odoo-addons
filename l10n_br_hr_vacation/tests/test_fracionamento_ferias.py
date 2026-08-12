# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Dias de direito da alocação e fracionamento das férias (RF-19).

CLT art. 130: os dias de direito (30/24/18/12/0) vêm da alocação
(hr.leave.allocation), conforme as faltas injustificadas no período
aquisitivo. CLT art. 134 §1º (Lei 13.467/2017): as férias podem ser
fracionadas em até 3 períodos, um deles com pelo menos 14 dias corridos e
os demais com pelo menos 5 dias corridos cada. O holerite de férias paga
os dias DO PERÍODO efetivamente gozado nesta fração, não o saldo inteiro.
"""
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import VacationCommon


@tagged("post_install", "-at_install")
class TestFracionamentoFerias(VacationCommon):
    """Fracionamento e dias de direito via alocação vinculada."""

    def _allocation(self, emp, faltas=0, date_from=None, date_to=None):
        alloc = self.env["hr.leave.allocation"].create(
            {
                "employee_id": emp.id,
                "holiday_status_id": self.leave_type_ferias.id,
                "date_from": date_from or date(2023, 1, 1),
                "date_to": date_to or date(2023, 12, 31),
            }
        )
        alloc.write({"l10n_br_faltas_periodo_aquisitivo": faltas})
        alloc.action_validate()
        return alloc

    def _payslip_ferias(self, emp, contract, alloc, dias_gozados, dias_abono=0):
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Férias - Fração",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": self.structure_ferias.id,
                "date_from": date(2024, 1, 1),
                "date_to": date(2024, 1, 31),
                "l10n_br_ferias_allocation_id": alloc.id,
                "l10n_br_dias_periodo_gozado": dias_gozados,
                "l10n_br_dias_abono": dias_abono,
                "company_id": self.env.company.id,
            }
        )
        return payslip

    def test_dias_direito_sem_write_explicito_nas_faltas(self):
        """Regressão: alocação criada SEM write() explícito em
        l10n_br_faltas_periodo_aquisitivo (só create() com holiday_status_id
        e datas) precisa computar os 30 dias de direito mesmo assim — o
        @api.depends do compute não pode depender apenas do campo de faltas,
        senão a criação direta (sem tocar nas faltas) nunca recomputa e o
        valor fica no default nativo do hr_holidays (1 dia)."""
        emp = self._create_employee()
        alloc = self.env["hr.leave.allocation"].create(
            {
                "employee_id": emp.id,
                "holiday_status_id": self.leave_type_ferias.id,
                "date_from": date(2023, 1, 1),
                "date_to": date(2023, 12, 31),
            }
        )
        alloc.action_validate()
        self.assertEqual(alloc.number_of_days, 30)

    def test_dias_direito_expostos_no_holerite(self):
        """Alocação com 10 faltas → 24 dias de direito, exibidos no holerite."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        alloc = self._allocation(emp, faltas=10)
        self.assertEqual(alloc.number_of_days, 24)
        payslip = self._payslip_ferias(emp, contract, alloc, dias_gozados=24)
        self.assertEqual(payslip.l10n_br_dias_direito_ferias, 24)

    def test_paga_apenas_os_dias_do_periodo_gozado(self):
        """Fração de 14 dias de um direito de 30: paga 14/30, não 30/30."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=6000.00)
        alloc = self._allocation(emp, faltas=0)
        payslip = self._payslip_ferias(emp, contract, alloc, dias_gozados=14)
        payslip.compute_sheet()
        self.assertEqual(payslip.l10n_br_dias_ferias_gozadas, 14)
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "FERIAS"), 6000.00 * 14 / 30
        )

    def test_fracionamento_3_periodos_validos(self):
        """14 + 10 + 6 dias: um período >= 14, os demais >= 5. Sem erro."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        alloc = self._allocation(emp, faltas=0)
        p1 = self._payslip_ferias(emp, contract, alloc, dias_gozados=14)
        p2 = self._payslip_ferias(emp, contract, alloc, dias_gozados=10)
        p3 = self._payslip_ferias(emp, contract, alloc, dias_gozados=6)
        for p in (p1, p2, p3):
            p.compute_sheet()  # não deve levantar ValidationError

    def test_fracionamento_4_periodos_bloqueado(self):
        """Mais de 3 frações no mesmo período aquisitivo: bloqueado.

        As 3 primeiras frações (14+8+6=28) já satisfazem a regra do art.
        134 §1º (uma >= 14, as demais >= 5); o bloqueio testado aqui é
        especificamente o LIMITE DE 3 períodos, não os mínimos de dias.
        """
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        alloc = self._allocation(emp, faltas=0)
        for dias in (14, 8, 6):
            self._payslip_ferias(emp, contract, alloc, dias_gozados=dias)
        with self.assertRaises(ValidationError):
            self._payslip_ferias(emp, contract, alloc, dias_gozados=1)

    def test_fracionamento_sem_periodo_de_14_dias_bloqueado(self):
        """10 + 10 + 10 dias: nenhum período com 14 dias ou mais → bloqueado."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        alloc = self._allocation(emp, faltas=0)
        self._payslip_ferias(emp, contract, alloc, dias_gozados=10)
        with self.assertRaises(ValidationError):
            self._payslip_ferias(emp, contract, alloc, dias_gozados=10)

    def test_fracionamento_periodo_menor_5_dias_bloqueado(self):
        """20 + 4 dias: a segunda fração tem menos de 5 dias → bloqueado."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        alloc = self._allocation(emp, faltas=0)
        self._payslip_ferias(emp, contract, alloc, dias_gozados=20)
        with self.assertRaises(ValidationError):
            self._payslip_ferias(emp, contract, alloc, dias_gozados=4)

    def test_soma_gozado_mais_vendido_nao_pode_superar_direito(self):
        """20 dias gozados + 15 vendidos (35) supera os 30 de direito."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        alloc = self._allocation(emp, faltas=0)
        with self.assertRaises(ValidationError):
            self._payslip_ferias(emp, contract, alloc, dias_gozados=20, dias_abono=15)

    def test_abono_limitado_a_um_terco_do_direito(self):
        """Direito de 24 dias (10 faltas): abono máximo é 8 dias (24/3)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        alloc = self._allocation(emp, faltas=10)
        self.assertEqual(alloc.number_of_days, 24)
        with self.assertRaises(ValidationError):
            self._payslip_ferias(emp, contract, alloc, dias_gozados=15, dias_abono=9)

    def test_abono_pelo_novo_caminho_gera_verba(self):
        """l10n_br_dias_abono > 0 (com alocação) dispara a rubrica de abono
        mesmo sem marcar o campo legado l10n_br_abono_pecuniario."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        alloc = self._allocation(emp, faltas=0)
        payslip = self._payslip_ferias(
            emp, contract, alloc, dias_gozados=20, dias_abono=10
        )
        payslip.compute_sheet()
        self.assertFalse(payslip.l10n_br_abono_pecuniario)
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "ABONO_PECUNIARIO"), 3000.00 * 10 / 30
        )
