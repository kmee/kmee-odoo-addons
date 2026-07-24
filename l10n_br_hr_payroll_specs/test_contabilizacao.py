# Copyright 2024 ABGF
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""
TDD: Contabilização da Folha de Pagamento.

Cobertura:
  - Geração de journal entries ao confirmar folha
  - Partidas corretas para salário, INSS, IRRF, FGTS
  - Contabilização de férias e 13º
  - Reversão de lançamentos ao reabrir folha
  - Balanceamento do lançamento (débito = crédito)
"""

from .common import PayrollCommon


class TestContabilizacaoFolha(PayrollCommon):
    """Testes dos lançamentos contábeis da folha."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Configura plano de contas simplificado para testes
        cls.account_salarios = cls.env["account.account"].create(
            {
                "name": "Despesas com Salários",
                "code": "6.1.1.01",
                "account_type": "expense",
                "company_id": cls.company.id,
            }
        )
        cls.account_inss_empregado = cls.env["account.account"].create(
            {
                "name": "INSS a Recolher (Empregado)",
                "code": "2.1.3.01",
                "account_type": "liability_current",
                "company_id": cls.company.id,
            }
        )
        cls.account_inss_empresa = cls.env["account.account"].create(
            {
                "name": "INSS a Recolher (Empresa)",
                "code": "2.1.3.02",
                "account_type": "liability_current",
                "company_id": cls.company.id,
            }
        )
        cls.account_irrf = cls.env["account.account"].create(
            {
                "name": "IRRF a Recolher",
                "code": "2.1.3.03",
                "account_type": "liability_current",
                "company_id": cls.company.id,
            }
        )
        cls.account_fgts = cls.env["account.account"].create(
            {
                "name": "FGTS a Recolher",
                "code": "2.1.3.04",
                "account_type": "liability_current",
                "company_id": cls.company.id,
            }
        )
        cls.account_salarios_a_pagar = cls.env["account.account"].create(
            {
                "name": "Salários a Pagar",
                "code": "2.1.1.01",
                "account_type": "liability_current",
                "company_id": cls.company.id,
            }
        )

    def test_confirmar_folha_gera_journal_entry(self):
        """Confirmar folha deve gerar um lançamento contábil (account.move)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        # Antes de confirmar: sem lançamento
        self.assertFalse(
            payslip.move_id, msg="Folha em rascunho não deve ter lançamento contábil"
        )
        # Confirmar folha
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

    def test_reabrir_folha_estorna_lancamento(self):
        """Reabrir folha confirmada deve criar lançamento de estorno."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.action_payslip_done()
        move_original = payslip.move_id
        # Reabrir folha
        payslip.action_payslip_cancel()
        payslip.action_payslip_draft()
        # O lançamento original deve estar cancelado/revertido
        self.assertIn(
            move_original.state,
            ["cancel", "draft"],
            msg="Lançamento original deve ser cancelado ao reabrir folha",
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


class TestContabilizacaoFerias(PayrollCommon):
    """Testes de contabilização de férias e provisão."""

    def test_provisao_ferias_mensal(self):
        """Deve ser criada provisão mensal de férias (1/12 por mês)."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=6000.00)
        payslip = self._create_payslip(emp, contract)
        payslip.action_payslip_done()
        # Verifica provisão de férias no lançamento
        move = payslip.move_id
        provisao = move.line_ids.filtered(
            lambda line: "provisao_ferias" in (line.account_id.code or "").lower()
            or "ferias" in (line.name or "").lower()
        )
        # Se o módulo de provisão de férias estiver ativo
        if self.env["ir.module.module"].search(
            [("name", "=", "l10n_br_hr_vacation"), ("state", "=", "installed")]
        ):
            self.assertTrue(
                provisao, msg="Deve haver linha de provisão de férias no lançamento"
            )
