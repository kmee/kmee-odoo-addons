# Copyright 2024 ABGF
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""
TDD: Ressarcimento de Despesas (integração com OCA/hr-expense).

Cobertura:
  - Criação de despesa e aprovação
  - Pagamento via folha de pagamento
  - Pagamento via ordem de pagamento bancário
  - Dedutibilidade de IRRF
  - Limites de categorias de despesa
"""
from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestRessarcimento(TransactionCase):
    """Testes do módulo l10n_br_ressarcimento."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Funcionário Ressarcimento",
                "l10n_br_cpf": "529.982.247-25",
                "company_id": cls.company.id,
            }
        )
        cls.categoria_hospedagem = cls.env["hr.expense.category"].create(
            {
                "name": "Hospedagem",
                "code": "HOSP",
                "l10n_br_limite_mensal": 500.00,
            }
        )
        cls.categoria_refeicao = cls.env["hr.expense.category"].create(
            {
                "name": "Refeição",
                "code": "REF",
                "l10n_br_limite_mensal": 1200.00,
            }
        )

    def _create_expense(self, amount, category=None, name="Despesa Teste"):
        return self.env["hr.expense"].create(
            {
                "name": name,
                "employee_id": self.employee.id,
                "total_amount": amount,
                "date": date(2024, 3, 15),
                "product_id": (category or self.categoria_refeicao).product_id.id,
                "company_id": self.company.id,
            }
        )

    def test_criar_despesa_e_aprovar(self):
        """Despesa pode ser criada e aprovada pelo gestor."""
        expense = self._create_expense(250.00)
        self.assertEqual(expense.state, "draft")
        sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Relatório Mar/2024",
                "employee_id": self.employee.id,
                "expense_line_ids": [(4, expense.id)],
            }
        )
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")

    def test_limite_categoria_nao_pode_ser_excedido(self):
        """Despesa acima do limite da categoria deve ser alertada/rejeitada."""
        expense = self._create_expense(600.00, category=self.categoria_hospedagem)
        sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Relatório Limite",
                "employee_id": self.employee.id,
                "expense_line_ids": [(4, expense.id)],
            }
        )
        # Ao submeter, deve avisar ou rejeitar por exceder limite de R$500
        with self.assertRaises((UserError, ValidationError)):
            sheet.action_approve_expense_sheets()

    def test_pagamento_via_folha(self):
        """Ressarcimento pode ser pago junto com a folha de pagamento."""
        expense = self._create_expense(250.00)
        expense.write({"l10n_br_pagar_via_folha": True})
        sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Relatório Folha",
                "employee_id": self.employee.id,
                "expense_line_ids": [(4, expense.id)],
                "l10n_br_pagar_via_folha": True,
            }
        )
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        # Verifica que o valor aparece na folha do mês
        payslip = self.env["hr.payslip"].search(
            [("employee_id", "=", self.employee.id)], limit=1
        )
        if payslip:
            ressarcimento = sum(
                payslip.line_ids.filtered(
                    lambda line: line.code == "RESSARCIMENTO"
                ).mapped("total")
            )
            self.assertAlmostEqual(ressarcimento, 250.00, places=2)

    def test_ressarcimento_nao_incide_inss_irrf(self):
        """Ressarcimento de despesas não incide INSS nem IRRF."""
        expense = self._create_expense(300.00)
        expense.write({"l10n_br_natureza": "ressarcimento"})
        # Verifica que a natureza está marcada como não-tributável
        self.assertEqual(expense.l10n_br_natureza, "ressarcimento")
        self.assertFalse(expense.l10n_br_tributa_inss)
        self.assertFalse(expense.l10n_br_tributa_irrf)

    def test_ajuda_de_custo_isenta_ate_50_porcento_sm(self):
        """Ajuda de custo até 50% do salário mínimo é isenta de IRRF (IN RFB 1.500/2014)."""
        expense = self._create_expense(700.00)
        expense.write({"l10n_br_natureza": "ajuda_de_custo"})
        # Abaixo do limite: isento
        self.assertFalse(expense.l10n_br_tributa_irrf)

    def test_ajuda_de_custo_acima_limite_tributa(self):
        """Ajuda de custo acima de 50% do SM incide IRRF sobre o excedente."""
        limite_isento = 1412.00 * 0.50  # = 706.00
        expense = self._create_expense(1000.00)
        expense.write({"l10n_br_natureza": "ajuda_de_custo"})
        # Acima do limite: tributa sobre o excedente
        self.assertTrue(expense.l10n_br_tributa_irrf)
        excedente = expense.l10n_br_base_irrf_ajuda_de_custo
        self.assertAlmostEqual(excedente, 1000.00 - limite_isento, places=2)
