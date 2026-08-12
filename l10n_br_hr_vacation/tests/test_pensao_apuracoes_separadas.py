# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes ORM: pensão alimentícia (RF-03) e desconto simplificado (RF-16) nas
apurações SEPARADAS de férias, 13º salário e rescisão.

Regra fiscal validada aqui (documentada no cabeçalho de
``data/hr_salary_rule_ferias_data.xml``):

  - só se deduz da base do IRRF a pensão EFETIVAMENTE RETIDA no holerite
    (Lei 9.250/95 art. 4º II: importância PAGA a título de pensão; IN RFB
    1.500/2014, art. 13, § 6º, I, que exige deduções correspondentes ao
    rendimento e veda usar o mesmo valor em outra base, e art. 29, § 3º);
  - a parcela FIXA é obrigação mensal e é descontada UMA vez por mês, na folha
    mensal - não se repete em férias nem no 13º (seria desconto em dobro do
    empregado e dedução em dobro da mesma importância);
  - a parcela PERCENTUAL incide sobre a verba da própria apuração (férias +
    1/3, 13º bruto, saldo de salário), sem sobreposição com a folha mensal;
  - na rescisão não existe folha mensal: o saldo de salário ocupa esse lugar e
    recebe a parcela fixa;
  - o IRRF de cada apuração é retido pela forma mais favorável (dedução legal
    x desconto simplificado da Lei 9.250/95, art. 4º, § 2º, cuja opção a IN RFB
    2.141/2023 inseriu em cada base: art. 13, § 8º para o 13º, art. 29, § 5º
    para as férias e art. 52, § 3º para a folha mensal).

Competências usadas: 2024 (tabela IRRF vigente de 02/2024 a 04/2025, isenção
até R$2.259,20 e desconto simplificado de R$564,80 = 25% da isenção).
"""
from datetime import date

from odoo.tests import tagged

from .common import VacationCommon

# 25% do teto da faixa de isenção da tabela vigente em 2024 (R$2.259,20).
DESCONTO_SIMPLIFICADO_2024 = 564.80


@tagged("post_install", "-at_install")
class TestPensaoFerias(VacationCommon):
    """Pensão alimentícia no holerite de férias."""

    def _ferias(self, emp, contract, ano=2024, mes=5):
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Férias - Pensão",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(ano, mes, 1),
                "date_to": date(ano, mes, 30),
                "struct_id": self.structure_ferias.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    def _mensal(self, emp, contract, ano=2024, mes=5):
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Mensal - Pensão",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(ano, mes, 1),
                "date_to": date(ano, mes, 30),
                "struct_id": self.structure_clt.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    def test_pensao_percentual_retida_e_deduzida_da_base(self):
        """Pensão de 20% sobre férias de R$6.000 + 1/3 (GROSS R$8.000).

        Conferência à mão:
          pensão   = 20% x 8.000,00           = 1.600,00
          INSS     = tabela 2024 sobre 8.000  =   908,86
          base     = 8.000 - 908,86 - 1.600   = 5.491,14
          IRRF     = 27,5% x 5.491,14 - 896   =   614,06
          (simplificado: 8.000 - 564,80 = 7.435,20 -> 1.148,68, mais caro)
          líquido  = 8.000 - 908,86 - 1.600 - 614,06 = 4.877,08
        """
        emp = self._create_employee()
        emp.write({"l10n_br_pensao_percentual": 20.0})
        contract = self._create_contract(emp, wage=6000.00)
        payslip = self._ferias(emp, contract)

        self.assertAlmostEqualMoney(self._get_line_total(payslip, "GROSS"), 8000.00)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "INSS"), 908.86)
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "PENSAO_ALIMENTICIA"), 1600.00
        )
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "BASE_IRRF"), 5491.14)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "IRRF"), 614.06)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "NET"), 4877.08)

    def test_pensao_percentual_reduz_o_irrf_das_ferias(self):
        """A retenção da pensão derruba o IRRF frente a quem não tem pensão."""
        com_pensao = self._create_employee("Com Pensão")
        com_pensao.write({"l10n_br_pensao_percentual": 20.0})
        sem_pensao = self._create_employee("Sem Pensão")
        slip_com = self._ferias(com_pensao, self._create_contract(com_pensao, 6000.00))
        slip_sem = self._ferias(sem_pensao, self._create_contract(sem_pensao, 6000.00))

        self.assertLess(
            self._get_line_total(slip_com, "IRRF"),
            self._get_line_total(slip_sem, "IRRF"),
        )
        # A diferença das bases é exatamente a pensão retida.
        self.assertAlmostEqualMoney(
            self._get_line_total(slip_sem, "BASE_IRRF")
            - self._get_line_total(slip_com, "BASE_IRRF"),
            self._get_line_total(slip_com, "PENSAO_ALIMENTICIA"),
        )

    def test_pensao_fixa_nao_entra_nas_ferias(self):
        """Parcela FIXA é mensal: não é retida nem deduzida no holerite de férias.

        Antes a base do IRRF das férias era reduzida pela parcela fixa SEM que
        ela fosse retida - dedução inexistente (subtributação) e, se replicada,
        desconto em dobro do empregado.
        """
        emp = self._create_employee()
        emp.write({"l10n_br_pensao_alimenticia": 1000.00})
        contract = self._create_contract(emp, wage=6000.00)
        ferias = self._ferias(emp, contract)

        # Nenhuma retenção de pensão no holerite de férias.
        self.assertAlmostEqualMoney(
            self._get_line_total(ferias, "PENSAO_ALIMENTICIA"), 0.0
        )
        # Base = GROSS - INSS (a parcela fixa NÃO reduz a base aqui).
        inss = self._get_line_total(ferias, "INSS")
        self.assertAlmostEqualMoney(
            self._get_line_total(ferias, "BASE_IRRF"), 8000.00 - inss
        )
        # E a parcela fixa continua sendo descontada uma vez, na folha mensal.
        mensal = self._mensal(emp, contract)
        self.assertAlmostEqualMoney(
            self._get_line_total(mensal, "PENSAO_ALIMENTICIA"), 1000.00
        )

    def test_sem_dupla_deducao_entre_mensal_e_ferias(self):
        """Fixo R$500 + 10%: no mês há mensal E férias, a fixa entra uma vez.

        Total retido no mês = 500 (fixa, uma vez) + 10% de cada verba
        (6.000 do salário + 8.000 das férias) = 500 + 1.400 = 1.900.
        """
        emp = self._create_employee()
        emp.write(
            {
                "l10n_br_pensao_alimenticia": 500.00,
                "l10n_br_pensao_percentual": 10.0,
            }
        )
        contract = self._create_contract(emp, wage=6000.00)
        mensal = self._mensal(emp, contract)
        ferias = self._ferias(emp, contract)

        pensao_mensal = self._get_line_total(mensal, "PENSAO_ALIMENTICIA")
        pensao_ferias = self._get_line_total(ferias, "PENSAO_ALIMENTICIA")
        # Mensal: 500 + 10% x 6.000. Férias: só 10% x 8.000.
        self.assertAlmostEqualMoney(pensao_mensal, 1100.00)
        self.assertAlmostEqualMoney(pensao_ferias, 800.00)
        self.assertAlmostEqualMoney(pensao_mensal + pensao_ferias, 1900.00)
        # A parcela fixa aparece uma única vez no mês.
        self.assertAlmostEqualMoney(
            pensao_mensal + pensao_ferias - 0.10 * (6000.00 + 8000.00), 500.00
        )


@tagged("post_install", "-at_install")
class TestPensaoDecimoTerceiro(VacationCommon):
    """Pensão alimentícia na apuração exclusiva de fonte do 13º."""

    def _decimo(self, emp, contract, structure=None):
        payslip = self.env["hr.payslip"].create(
            {
                "name": "13º - Pensão",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 12, 1),
                "date_to": date(2024, 12, 31),
                "struct_id": (structure or self.structure_13).id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    def test_pensao_percentual_retida_e_deduzida_da_base_do_13(self):
        """Pensão de 20% sobre 13º de R$6.000.

        Conferência à mão:
          pensão   = 20% x 6.000,00              = 1.200,00
          INSS_13  = tabela 2024 sobre 6.000     =   658,82
          base     = 6.000 - 658,82 - 1.200      = 4.141,18
          IRRF_13  = 22,5% x 4.141,18 - 662,77   =   269,00
          (simplificado: 6.000 - 564,80 = 5.435,20 -> 598,68, mais caro)
          líquido  = 6.000 - 658,82 - 1.200 - 269,00 = 3.872,18
        """
        emp = self._create_employee()
        emp.write({"l10n_br_pensao_percentual": 20.0})
        contract = self._create_contract(emp, wage=6000.00, date_start=date(2024, 1, 1))
        payslip = self._decimo(emp, contract)

        self.assertAlmostEqualMoney(self._get_line_total(payslip, "INSS_13"), 658.82)
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "PENSAO_ALIMENTICIA_13"), 1200.00
        )
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "BASE_IRRF_13"), 4141.18
        )
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "IRRF_13"), 269.00)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "NET"), 3872.18)

    def test_pensao_fixa_nao_entra_no_13(self):
        """Parcela fixa é mensal: nem retida nem deduzida da base do 13º."""
        emp = self._create_employee()
        emp.write({"l10n_br_pensao_alimenticia": 1000.00})
        contract = self._create_contract(emp, wage=6000.00, date_start=date(2024, 1, 1))
        payslip = self._decimo(emp, contract)

        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "PENSAO_ALIMENTICIA_13"), 0.0
        )
        inss_13 = self._get_line_total(payslip, "INSS_13")
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "BASE_IRRF_13"), 6000.00 - inss_13
        )

    def test_primeira_parcela_nao_retem_pensao(self):
        """1ª parcela é adiantamento: sem INSS, sem IRRF e sem pensão.

        A pensão percentual sobre o 13º é retida integralmente na apuração que
        FECHA o 13º (2ª parcela), como já ocorre com INSS e IRRF - evita retê-la
        duas vezes sobre a mesma gratificação.
        """
        emp = self._create_employee()
        emp.write({"l10n_br_pensao_percentual": 20.0})
        contract = self._create_contract(emp, wage=6000.00, date_start=date(2024, 1, 1))
        primeira = self.env["hr.payslip"].create(
            {
                "name": "13º 1ª parcela - Pensão",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 11, 1),
                "date_to": date(2024, 11, 30),
                "struct_id": self.structure_13_primeira.id,
                "company_id": self.env.company.id,
            }
        )
        primeira.compute_sheet()

        self.assertAlmostEqualMoney(
            self._get_line_total(primeira, "ADIANTAMENTO_13"), 3000.00
        )
        self.assertAlmostEqualMoney(
            self._get_line_total(primeira, "PENSAO_ALIMENTICIA_13"), 0.0
        )
        self.assertAlmostEqualMoney(self._get_line_total(primeira, "NET"), 3000.00)
        # Na 2ª parcela a pensão incide sobre o 13º INTEGRAL, uma única vez.
        segunda = self._decimo(emp, contract, structure=self.structure_13_segunda)
        self.assertAlmostEqualMoney(
            self._get_line_total(segunda, "PENSAO_ALIMENTICIA_13"), 1200.00
        )


@tagged("post_install", "-at_install")
class TestPensaoRescisao(VacationCommon):
    """Pensão alimentícia na rescisão: fixa no saldo, percentual em cada verba."""

    def _rescisao(self, emp, contract):
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Rescisão - Pensão",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 6, 1),
                "date_to": date(2024, 6, 30),
                "struct_id": self.structure_rescisao.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    def test_pensao_fixa_e_percentual_na_rescisao(self):
        """Fixo R$500 + 10%, wage 6.000, desligamento em 30/06/2024.

        Conferência à mão:
          saldo de salário     = 6.000,00 (30/30 dias)
          13º proporcional     = 6/12 x 6.000       = 3.000,00
          pensão do saldo      = 500 + 10% x 6.000  = 1.100,00
          pensão do 13º        = 10% x 3.000        =   300,00 (sem a fixa)
          INSS saldo           =   658,82   INSS 13º =   258,82
          base IRRF saldo      = 6.000 - 658,82 - 1.100    = 4.241,18
          IRRF saldo           = 22,5% x 4.241,18 - 662,77 =   291,50
          base IRRF 13º        = 3.000 - 258,82 - 300      = 2.441,18
          IRRF 13º             = simplificado (2.435,20 -> 13,20) vence os
                                 13,65 da dedução legal    =    13,20
        """
        emp = self._create_employee("Rescisão Pensão")
        emp.write(
            {
                "l10n_br_pensao_alimenticia": 500.00,
                "l10n_br_pensao_percentual": 10.0,
            }
        )
        contract = self._create_contract(emp, wage=6000.00, date_start=date(2024, 1, 1))
        payslip = self._rescisao(emp, contract)
        g = self._get_line_total

        self.assertAlmostEqualMoney(g(payslip, "SALDO_SALARIO"), 6000.00)
        self.assertAlmostEqualMoney(g(payslip, "DECIMO_RESCISAO"), 3000.00)
        # A parcela fixa entra UMA vez, no saldo de salário (que faz o papel da
        # remuneração do mês; na rescisão não há folha mensal).
        self.assertAlmostEqualMoney(g(payslip, "PENSAO_ALIMENTICIA"), 1100.00)
        self.assertAlmostEqualMoney(g(payslip, "PENSAO_ALIMENTICIA_13"), 300.00)
        self.assertAlmostEqualMoney(g(payslip, "BASE_IRRF"), 4241.18)
        self.assertAlmostEqualMoney(g(payslip, "BASE_IRRF_13"), 2441.18)
        self.assertAlmostEqualMoney(g(payslip, "IRRF"), 291.50)
        self.assertAlmostEqualMoney(g(payslip, "IRRF_13"), 13.20)

    def test_net_da_rescisao_desconta_as_duas_pensoes(self):
        """O líquido da rescisão subtrai a pensão do saldo e a do 13º."""
        emp = self._create_employee("Rescisão Pensão NET")
        emp.write(
            {
                "l10n_br_pensao_alimenticia": 500.00,
                "l10n_br_pensao_percentual": 10.0,
            }
        )
        contract = self._create_contract(emp, wage=6000.00, date_start=date(2024, 1, 1))
        payslip = self._rescisao(emp, contract)
        g = self._get_line_total

        esperado = (
            g(payslip, "SALDO_SALARIO")
            + g(payslip, "DECIMO_RESCISAO")
            + g(payslip, "FERIAS_INDENIZADAS")
            + g(payslip, "ADICIONAL_FERIAS_INDENIZADAS")
            - g(payslip, "INSS")
            - g(payslip, "INSS_13")
            - g(payslip, "IRRF")
            - g(payslip, "IRRF_13")
            - g(payslip, "PENSAO_ALIMENTICIA")
            - g(payslip, "PENSAO_ALIMENTICIA_13")
        )
        self.assertAlmostEqualMoney(g(payslip, "NET"), esperado)
        self.assertGreater(g(payslip, "PENSAO_ALIMENTICIA"), 0.0)

    def test_ferias_indenizadas_nao_sofrem_pensao(self):
        """Verbas indenizatórias ficam fora da pensão nesta implementação.

        Decisão documentada (hr_salary_rule_rescisao_data.xml): a incidência da
        pensão sobre férias indenizadas e o seu 1/3 depende de decisão judicial
        específica, e não se presume. Como também não sofrem IRRF, nada muda na
        base do imposto.
        """
        emp = self._create_employee("Rescisão Indenizatórias")
        emp.write({"l10n_br_pensao_percentual": 10.0})
        contract = self._create_contract(emp, wage=6000.00, date_start=date(2024, 1, 1))
        payslip = self._rescisao(emp, contract)
        g = self._get_line_total

        self.assertGreater(g(payslip, "FERIAS_INDENIZADAS"), 0.0)
        # A pensão do saldo é 10% do saldo, e não 10% do total pago.
        self.assertAlmostEqualMoney(
            g(payslip, "PENSAO_ALIMENTICIA"), 0.10 * g(payslip, "SALDO_SALARIO")
        )


@tagged("post_install", "-at_install")
class TestDescontoSimplificadoApuracoesSeparadas(VacationCommon):
    """RF-16: a forma mais favorável também vale em férias, 13º e rescisão."""

    def test_simplificado_reduz_o_irrf_das_ferias(self):
        """Férias de wage 2.600 (GROSS 3.466,67), 05/2024.

        Dedução legal: base 3.466,67 - 314,82 (INSS) = 3.151,85 ->
        15% - 381,44 = 91,34.
        Desconto simplificado: 3.466,67 - 564,80 = 2.901,87 ->
        15% - 381,44 = 53,84 (MENOR, é o que deve ser retido).
        """
        emp = self._create_employee("Simplificado Férias")
        contract = self._create_contract(emp, wage=2600.00)
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Férias - Simplificado",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 5, 1),
                "date_to": date(2024, 5, 30),
                "struct_id": self.structure_ferias.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()

        self.assertAlmostEqualMoney(self._get_line_total(payslip, "GROSS"), 3466.67)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "INSS"), 314.82)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "BASE_IRRF"), 3151.85)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "IRRF"), 53.84)

    def test_simplificado_zera_o_irrf_do_13(self):
        """13º de R$2.600 em 12/2024: o simplificado leva a base à isenção.

        Dedução legal: 2.600 - 212,82 = 2.387,18 -> 7,5% - 169,44 = 9,60.
        Simplificado: 2.600 - 564,80 = 2.035,20 < 2.259,20 -> ISENTO.
        """
        emp = self._create_employee("Simplificado 13")
        contract = self._create_contract(emp, wage=2600.00, date_start=date(2024, 1, 1))
        payslip = self.env["hr.payslip"].create(
            {
                "name": "13º - Simplificado",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 12, 1),
                "date_to": date(2024, 12, 31),
                "struct_id": self.structure_13.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()

        self.assertAlmostEqualMoney(self._get_line_total(payslip, "INSS_13"), 212.82)
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "BASE_IRRF_13"), 2387.18
        )
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "IRRF_13"), 0.0)

    def test_simplificado_nao_piora_a_retencao(self):
        """Salário alto: a dedução legal continua vencendo (nada regride).

        Férias de wage 6.000 (GROSS 8.000): legal 1.054,06 <
        simplificado 1.148,68.
        """
        emp = self._create_employee("Legal Vence")
        contract = self._create_contract(emp, wage=6000.00)
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Férias - Legal vence",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "date_from": date(2024, 5, 1),
                "date_to": date(2024, 5, 30),
                "struct_id": self.structure_ferias.id,
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "IRRF"), 1054.06)
