# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Contabilização da Folha de Pagamento.

Cobertura:
  - Mapeamento regra→conta ENTREGUE pelo módulo (não montado no teste)
  - Geração de journal entry ao confirmar folha
  - Balanceamento do lançamento (débito = crédito)
  - Débito em conta de despesa e crédito em passivo
  - Reversão de lançamento ao reabrir folha
"""
from datetime import date

from odoo.addons.l10n_br_hr_payroll.tests.common import PayrollCommon


class TestContabilizacaoFolha(PayrollCommon):
    """Testes dos lançamentos contábeis da folha usando o mapeamento do módulo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        SalaryRule = cls.env["hr.salary.rule"]

        # Garante que a empresa tenha, no mínimo, uma conta de despesa e uma de
        # passivo no plano de contas. Em bases de teste sem CoA carregado, cria
        # contas de fixture (o mapeamento do módulo escolherá contas por TIPO,
        # não estas especificamente — o vínculo continua sendo do módulo).
        Account = cls.env["account.account"]
        if not Account.search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.company.id)],
            limit=1,
        ):
            Account.create(
                {
                    "name": "Despesas com Pessoal (fixture)",
                    "code": "TST6101",
                    "account_type": "expense",
                    "company_id": cls.company.id,
                }
            )
        if not Account.search(
            [
                ("account_type", "=", "liability_current"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        ):
            Account.create(
                {
                    "name": "Obrigações Trabalhistas (fixture)",
                    "code": "TST2101",
                    "account_type": "liability_current",
                    "company_id": cls.company.id,
                }
            )

        # Mapeamento ENTREGUE pelo módulo (mesma rotina do post_init_hook).
        SalaryRule._l10n_br_setup_payroll_accounts(cls.company)

        cls.rule_salario = cls.env.ref("l10n_br_hr_payroll.hr_rule_salario_base")
        cls.rule_net = cls.env.ref("l10n_br_hr_payroll.hr_rule_net")
        cls.journal_folha = cls.env.ref(
            "l10n_br_hr_payroll_account.journal_folha_pagamento"
        )

    def _create_payslip(self, employee, contract, date_from=None, date_to=None):
        """Cria e calcula holerite no diário FOPAG entregue pelo módulo."""
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"Holerite - {employee.name}",
                "employee_id": employee.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date_from or date(2024, 3, 1),
                "date_to": date_to or date(2024, 3, 31),
                "company_id": self.company.id,
                "journal_id": self.journal_folha.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    def test_mapeamento_entregue_pelo_modulo(self):
        """O módulo vincula regras a contas e define o diário FOPAG."""
        self.assertTrue(
            self.rule_salario.account_debit,
            "Regra Salário Base deve ter conta de débito mapeada pelo módulo",
        )
        self.assertEqual(self.rule_salario.account_debit.account_type, "expense")
        self.assertTrue(
            self.rule_net.account_credit,
            "Regra Salário Líquido deve ter conta de crédito mapeada pelo módulo",
        )
        self.assertTrue(
            self.journal_folha.default_account_id,
            "Diário FOPAG deve ter conta padrão (balanceamento) definida",
        )

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
        """Lançamento deve ter débito na conta de despesa mapeada."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.action_payslip_done()
        move = payslip.move_id
        linhas_despesa = move.line_ids.filtered(
            lambda line: line.account_id == self.rule_salario.account_debit
        )
        self.assertTrue(
            linhas_despesa, msg="Deve haver débito na conta de despesas mapeada"
        )
        self.assertGreater(sum(linhas_despesa.mapped("debit")), 0.0)

    def test_credito_em_passivo(self):
        """Lançamento deve ter crédito em conta de passivo."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.action_payslip_done()
        move = payslip.move_id
        linhas_passivo = move.line_ids.filtered(
            lambda line: line.account_id.account_type.startswith("liability")
        )
        self.assertTrue(linhas_passivo, msg="Deve haver crédito em passivo")
        self.assertGreater(sum(linhas_passivo.mapped("credit")), 0.0)

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
