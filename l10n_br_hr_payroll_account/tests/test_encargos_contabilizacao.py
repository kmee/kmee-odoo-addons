# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: contabilização dos encargos patronais e das provisões (RF-34).

Cobertura:
  - o módulo entrega o mapeamento regra->conta dos encargos patronais e das
    provisões (débito de despesa x crédito de passivo, dos DOIS lados);
  - o lançamento do holerite carrega despesa de encargo e passivo a recolher,
    permanecendo balanceado;
  - no Simples anexo III o lançamento não tem encargo previdenciário (só FGTS),
    isto é, o custo contábil MUDA com o regime - que é o defeito que o RF-34
    corrige (hoje o custo sai idêntico para regimes diferentes);
  - a resolução de conta por slot escolhe a conta específica do tributo quando o
    plano de contas tem uma, e cai na conta genérica quando não tem.
"""
from datetime import date

from odoo.addons.l10n_br_hr_payroll.tests.common import PayrollCommon

SALARIO = 6000.00

REGRAS_PATRONAIS = (
    "l10n_br_hr_payroll.hr_rule_cpp_patronal",
    "l10n_br_hr_payroll.hr_rule_rat_patronal",
    "l10n_br_hr_payroll.hr_rule_terceiros_patronal",
    "l10n_br_hr_payroll.hr_rule_provisao_ferias",
    "l10n_br_hr_payroll.hr_rule_provisao_ferias_encargos",
    "l10n_br_hr_payroll.hr_rule_provisao_decimo",
    "l10n_br_hr_payroll.hr_rule_provisao_decimo_encargos",
)


class TestEncargosContabilizacao(PayrollCommon):
    """Lançamento contábil dos encargos patronais e das provisões."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        Account = cls.env["account.account"]
        cls.SalaryRule = cls.env["hr.salary.rule"]

        # Contas de fixture só para garantir que a empresa tem, no mínimo, uma
        # despesa e um passivo (bases de teste sem CoA). O vínculo continua
        # sendo feito pelo módulo, por TIPO/slot, não por estes registros.
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
        cls.SalaryRule._l10n_br_setup_payroll_accounts(cls.company)
        cls.journal_folha = cls.env.ref(
            "l10n_br_hr_payroll_account.journal_folha_pagamento"
        )

    def _payslip(self, tax_framework="3", simples_anexo=False):
        self.env.company.write(
            {
                "tax_framework": tax_framework,
                "l10n_br_hr_simples_anexo": simples_anexo,
                "l10n_br_hr_rat": "2",
                "l10n_br_hr_fap": 1.0,
                "l10n_br_hr_terceiros_padrao": 5.8,
            }
        )
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=SALARIO)
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"Holerite - {emp.name}",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date(2026, 3, 1),
                "date_to": date(2026, 3, 31),
                "company_id": self.company.id,
                "journal_id": self.journal_folha.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    def test_mapeamento_dos_encargos_entregue_pelo_modulo(self):
        """Toda rubrica patronal/provisão nasce com débito E crédito mapeados."""
        for xmlid in REGRAS_PATRONAIS:
            rule = self.env.ref(xmlid)
            self.assertTrue(
                rule.account_debit,
                "regra %s deve ter conta de DESPESA mapeada" % rule.code,
            )
            self.assertEqual(rule.account_debit.account_type, "expense")
            self.assertTrue(
                rule.account_credit,
                "regra %s deve ter conta de PASSIVO mapeada" % rule.code,
            )
            self.assertTrue(
                rule.account_credit.account_type.startswith("liability"),
                "regra %s deve creditar passivo" % rule.code,
            )

    def test_lancamento_com_encargo_patronal_balanceado(self):
        """Confirmar a folha lança os encargos e o move fecha (D = C)."""
        payslip = self._payslip(tax_framework="3")
        payslip.action_payslip_done()
        move = payslip.move_id
        self.assertTrue(move)
        self.assertAlmostEqualMoney(
            sum(move.line_ids.mapped("debit")), sum(move.line_ids.mapped("credit"))
        )
        cpp = self.env.ref("l10n_br_hr_payroll.hr_rule_cpp_patronal")
        linhas_cpp = move.line_ids.filtered(
            lambda line: line.account_id == cpp.account_credit
        )
        self.assertTrue(linhas_cpp, "a CPP patronal deve chegar ao lançamento")

    def test_custo_contabil_muda_com_o_regime(self):
        """Mesmo salário, custo contábil diferente: é o ponto do RF-34."""
        normal = self._payslip(tax_framework="3")
        normal.action_payslip_done()
        debito_normal = sum(normal.move_id.line_ids.mapped("debit"))

        simples = self._payslip(tax_framework="1", simples_anexo="iii")
        simples.action_payslip_done()
        debito_simples = sum(simples.move_id.line_ids.mapped("debit"))

        self.assertGreater(
            debito_normal,
            debito_simples,
            "no Simples anexo III não há CPP/RAT/terceiros: o custo é menor",
        )
        # A diferença é exatamente a soma das rubricas patronais ausentes mais
        # os encargos das provisões.
        self.assertAlmostEqualMoney(
            debito_normal - debito_simples,
            1200.00 + 120.00 + 348.00 + (238.67 - 53.33) + (179.00 - 40.00),
        )

    def test_slot_escolhe_conta_especifica_quando_existe(self):
        """Com conta própria do tributo no plano, o slot a encontra."""
        conta_fgts = self.env["account.account"].create(
            {
                "name": "FGTS a Recolher",
                "code": "TST2199",
                "account_type": "liability_current",
                "company_id": self.company.id,
            }
        )
        encontrada = self.SalaryRule._l10n_br_find_account(
            self.company, "liability_fgts"
        )
        self.assertEqual(encontrada, conta_fgts)

    def test_slot_sem_conta_especifica_cai_no_generico(self):
        """Sem conta com a palavra-chave, resolve pela primeira do tipo."""
        encontrada = self.SalaryRule._l10n_br_find_account(
            self.company, "liability_terceiros"
        )
        self.assertTrue(encontrada)
        self.assertTrue(encontrada.account_type.startswith("liability"))

    def test_holerite_de_outra_empresa_nao_usa_o_diario_alheio(self):
        """Holerite de outra empresa não pode nascer no diário do FOPAG desta.

        Sem isso o custo de uma empresa é contabilizado na outra, em silêncio.
        """
        outra = self.env["res.company"].create({"name": "Outra Empresa (teste)"})
        journal_outra = self.env["account.journal"].create(
            {
                "name": "Folha de Pagamento (Outra Empresa)",
                "code": "FPG2",
                "type": "general",
                "company_id": outra.id,
            }
        )
        emp = self.env["hr.employee"].create(
            {
                "name": "Funcionário de Outra Empresa",
                "company_id": outra.id,
                "l10n_br_tipo_contrato": "clt",
            }
        )
        contract = self.env["hr.contract"].create(
            {
                "name": "Contrato Outra Empresa",
                "employee_id": emp.id,
                "wage": SALARIO,
                "date_start": date(2024, 1, 1),
                "state": "open",
                "struct_id": self.structure_clt.id,
                "company_id": outra.id,
            }
        )
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Holerite Outra Empresa",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date(2026, 3, 1),
                "date_to": date(2026, 3, 31),
                "company_id": outra.id,
            }
        )
        self.assertEqual(
            payslip.journal_id,
            journal_outra,
            "o holerite deve usar o diário da PRÓPRIA empresa, não o FOPAG desta",
        )
