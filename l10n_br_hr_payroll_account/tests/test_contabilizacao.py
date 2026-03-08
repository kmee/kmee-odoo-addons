# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Contabilização da Folha de Pagamento.

Cobertura:
  - Geração de journal entries ao confirmar folha
  - Partidas corretas para salário, INSS, IRRF, FGTS
  - Reversão de lançamentos ao reabrir folha
  - Balanceamento do lançamento (débito = crédito)
"""
from datetime import date

from odoo.addons.l10n_br_hr_payroll.tests.common import PayrollCommon


class TestContabilizacaoFolha(PayrollCommon):
    """Testes dos lançamentos contábeis da folha."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Contas contábeis de teste
        cls.account_salarios = cls.env["account.account"].create(
            {
                "name": "Despesas com Salários",
                "code": "6.1.1.01",
                "account_type": "expense",
                "company_id": cls.env.company.id,
            }
        )
        cls.account_inss_empregado = cls.env["account.account"].create(
            {
                "name": "INSS a Recolher (Empregado)",
                "code": "2.1.3.01",
                "account_type": "liability_current",
                "company_id": cls.env.company.id,
            }
        )
        cls.account_irrf = cls.env["account.account"].create(
            {
                "name": "IRRF a Recolher",
                "code": "2.1.3.03",
                "account_type": "liability_current",
                "company_id": cls.env.company.id,
            }
        )
        cls.account_fgts = cls.env["account.account"].create(
            {
                "name": "FGTS a Recolher",
                "code": "2.1.3.04",
                "account_type": "liability_current",
                "company_id": cls.env.company.id,
            }
        )
        cls.account_fgts_despesa = cls.env["account.account"].create(
            {
                "name": "Despesas com FGTS",
                "code": "6.1.1.04",
                "account_type": "expense",
                "company_id": cls.env.company.id,
            }
        )
        cls.account_salarios_a_pagar = cls.env["account.account"].create(
            {
                "name": "Salários a Pagar",
                "code": "2.1.1.01",
                "account_type": "liability_current",
                "company_id": cls.env.company.id,
            }
        )

        # Diário de folha para testes
        cls.journal_folha = cls.env["account.journal"].create(
            {
                "name": "Folha de Pagamento - Teste",
                "code": "FOPT",
                "type": "general",
                "default_account_id": cls.account_salarios_a_pagar.id,
                "company_id": cls.env.company.id,
            }
        )

        # Mapear regras salariais → contas contábeis
        cls.env.ref("l10n_br_hr_payroll.hr_rule_salario_base").write(
            {"account_debit": cls.account_salarios.id}
        )
        cls.env.ref("l10n_br_hr_payroll.hr_rule_inss").write(
            {"account_credit": cls.account_inss_empregado.id}
        )
        cls.env.ref("l10n_br_hr_payroll.hr_rule_irrf").write(
            {"account_credit": cls.account_irrf.id}
        )
        cls.env.ref("l10n_br_hr_payroll.hr_rule_fgts").write(
            {
                "account_debit": cls.account_fgts_despesa.id,
                "account_credit": cls.account_fgts.id,
            }
        )
        cls.env.ref("l10n_br_hr_payroll.hr_rule_net").write(
            {"account_credit": cls.account_salarios_a_pagar.id}
        )

    def _create_payslip(self, employee, contract, date_from=None, date_to=None):
        """Override para definir journal_id nos testes de contabilização."""
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"Holerite - {employee.name}",
                "employee_id": employee.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date_from or date(2024, 3, 1),
                "date_to": date_to or date(2024, 3, 31),
                "company_id": self.env.company.id,
                "journal_id": self.journal_folha.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    def test_confirmar_folha_gera_journal_entry(self):
        """Confirmar folha deve gerar um lançamento contábil (account.move)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        self.assertFalse(
            payslip.move_id, msg="Folha em rascunho não deve ter lançamento contábil"
        )
        payslip.action_payslip_done()
        self.assertTrue(
            payslip.move_id, msg="Folha confirmada deve gerar lançamento contábil"
        )

    def test_lancamento_balanceado_debito_igual_credito(self):
        """Lançamento contábil deve ser balanceado (D = C)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.action_payslip_done()
        move = payslip.move_id
        total_debit = sum(move.line_ids.mapped("debit"))
        total_credit = sum(move.line_ids.mapped("credit"))
        self.assertAlmostEqualMoney(
            total_debit,
            total_credit,
            msg="Lançamento contábil deve ser balanceado (D = C)",
        )

    def test_debito_em_despesa_salarios(self):
        """Lançamento deve ter débito na conta de despesa com salários."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.action_payslip_done()
        move = payslip.move_id
        linhas_despesa = move.line_ids.filtered(
            lambda line: line.account_id == self.account_salarios
        )
        self.assertTrue(
            linhas_despesa, msg="Deve haver débito na conta de despesas com salários"
        )
        self.assertGreater(sum(linhas_despesa.mapped("debit")), 0.0)

    def test_credito_inss_passivo(self):
        """INSS retido do empregado deve gerar crédito em passivo."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        inss = self._get_line_total(payslip, "INSS")
        payslip.action_payslip_done()
        move = payslip.move_id
        linhas_inss = move.line_ids.filtered(
            lambda line: line.account_id == self.account_inss_empregado
        )
        self.assertTrue(linhas_inss, msg="Deve haver crédito na conta INSS a recolher")
        total_credito_inss = sum(linhas_inss.mapped("credit"))
        self.assertAlmostEqualMoney(total_credito_inss, inss)

    def test_credito_irrf_passivo(self):
        """IRRF retido deve gerar crédito em passivo."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=10000.00)
        payslip = self._create_payslip(emp, contract)
        irrf = self._get_line_total(payslip, "IRRF")
        payslip.action_payslip_done()
        move = payslip.move_id
        linhas_irrf = move.line_ids.filtered(
            lambda line: line.account_id == self.account_irrf
        )
        self.assertTrue(linhas_irrf)
        self.assertAlmostEqualMoney(sum(linhas_irrf.mapped("credit")), irrf)

    def test_reabrir_folha_remove_lancamento(self):
        """Reabrir folha confirmada deve remover/reverter o lançamento."""
        self.env["ir.config_parameter"].sudo().set_param(
            "payroll.allow_cancel_payslips", "True"
        )
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.action_payslip_done()
        self.assertTrue(payslip.move_id)
        payslip.action_payslip_cancel()
        payslip.action_payslip_draft()
        self.assertFalse(
            payslip.move_id,
            msg="Lançamento contábil deve ser removido ao reabrir folha",
        )

    def test_fgts_competencia_registrado_provisao(self):
        """FGTS da competência deve gerar provisão no passivo."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        fgts = self._get_line_total(payslip, "FGTS")
        payslip.action_payslip_done()
        move = payslip.move_id
        linhas_fgts = move.line_ids.filtered(
            lambda line: line.account_id == self.account_fgts
        )
        self.assertTrue(linhas_fgts, msg="Deve haver provisão de FGTS no passivo")
        self.assertAlmostEqualMoney(sum(linhas_fgts.mapped("credit")), fgts)
