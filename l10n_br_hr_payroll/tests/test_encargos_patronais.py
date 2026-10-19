# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes ORM dos encargos patronais e das provisões (RF-31 a RF-34).

Provam, no holerite calculado de verdade, que:
  - o custo do empregador aparece (CPP, RAT ajustado, terceiros) e NÃO é
    descontado do empregado;
  - o regime tributário da empresa muda o custo (Simples I-III/V não gera
    contribuição patronal; anexo IV gera CPP e RAT sem terceiros);
  - a transição da CPRB reduz SOMENTE a CPP, e no 13º pela coluna própria;
  - as provisões de férias/13º carregam os encargos do regime.

Todos usam o mesmo salário de R$ 6.000,00 e a competência 03/2026, de modo que
os valores sejam conferíveis à mão (ver a tabela no README do módulo).
"""
from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import PayrollCommon

SALARIO = 6000.00
COMPETENCIA_INICIO = date(2026, 3, 1)
COMPETENCIA_FIM = date(2026, 3, 31)


@tagged("post_install", "-at_install")
class EncargosPatronaisCommon(PayrollCommon):
    """Fixtures: empresa parametrizável por regime + holerite de R$ 6.000,00."""

    def _config_empresa(
        self,
        tax_framework="3",
        simples_anexo=False,
        rat="2",
        fap=1.0,
        terceiros=5.8,
        cprb_optante=False,
        perc_nao_desonerada=0.0,
        perc_ferias_indenizadas=0.0,
    ):
        """Configura a empresa do teste (rollback ao fim de cada teste)."""
        self.env.company.write(
            {
                "tax_framework": tax_framework,
                "l10n_br_hr_simples_anexo": simples_anexo,
                "l10n_br_hr_rat": rat,
                "l10n_br_hr_fap": fap,
                "l10n_br_hr_terceiros_padrao": terceiros,
                "l10n_br_hr_cprb_optante": cprb_optante,
                "l10n_br_hr_cprb_perc_contrib_nao_desonerada": perc_nao_desonerada,
                "l10n_br_hr_prov_ferias_perc_indenizado": perc_ferias_indenizadas,
            }
        )
        return self.env.company

    def _holerite(self, simples_anexo_contrato=False, date_from=None, date_to=None):
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=SALARIO)
        if simples_anexo_contrato:
            contract.l10n_br_hr_simples_anexo = simples_anexo_contrato
        return self._create_payslip(
            emp,
            contract,
            date_from=date_from or COMPETENCIA_INICIO,
            date_to=date_to or COMPETENCIA_FIM,
        )


class TestEncargosPorRegime(EncargosPatronaisCommon):
    """RF-31/RF-32: o custo patronal varia com o regime tributário."""

    def test_regime_normal_gera_cpp_rat_terceiros(self):
        """Lucro Real/Presumido: CPP 1.200 + RAT 120 (2%) + terceiros 348."""
        self._config_empresa(tax_framework="3", rat="2")
        payslip = self._holerite()
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "CPP"), 1200.00)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "RAT"), 120.00)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "TERCEIROS"), 348.00)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "FGTS"), 480.00)

    def test_encargo_patronal_nao_reduz_o_liquido(self):
        """Encargo é CUSTO: não desconta do empregado nem entra no NET."""
        self._config_empresa(tax_framework="3", rat="2")
        payslip = self._holerite()
        liquido = self._get_line_total(payslip, "NET")
        inss = self._get_line_total(payslip, "INSS")
        irrf = self._get_line_total(payslip, "IRRF")
        self.assertAlmostEqualMoney(
            liquido,
            SALARIO - inss - irrf,
            msg="o líquido só pode ser reduzido por descontos do empregado",
        )
        self.assertGreater(self._get_line_total(payslip, "CPP"), 0.0)

    def test_simples_anexo_iii_sem_encargo_patronal(self):
        """Simples anexo III: CPP/RAT/terceiros no DAS - só FGTS na folha."""
        self._config_empresa(tax_framework="1", simples_anexo="iii")
        payslip = self._holerite()
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "CPP"), 0.0)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "RAT"), 0.0)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "TERCEIROS"), 0.0)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "FGTS"), 480.00)
        self.assertFalse(
            payslip.line_ids.filtered(lambda line: line.code == "CPP"),
            "no Simples anexo III a rubrica de CPP não deve nem ser gerada",
        )

    def test_simples_anexo_iv_no_contrato_gera_cpp_e_rat(self):
        """Anexo IV declarado no CONTRATO de empresa anexo III (concomitância)."""
        self._config_empresa(tax_framework="1", simples_anexo="iii", rat="2")
        payslip = self._holerite(simples_anexo_contrato="iv")
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "CPP"), 1200.00)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "RAT"), 120.00)
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "TERCEIROS"),
            0.0,
            msg="terceiros são dispensados em todo o Simples (art. 13 §3º)",
        )

    def test_rat_ajustado_pelo_fap(self):
        """RAT ajustado = RAT x FAP, e é ele que incide sobre a remuneração."""
        company = self._config_empresa(tax_framework="3", rat="3", fap=0.7639)
        self.assertAlmostEqual(company.l10n_br_hr_rat_ajustado, 2.2917, places=4)
        payslip = self._holerite()
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "RAT"), 137.50)

    def test_fap_fora_da_faixa_legal_e_recusado(self):
        """FAP só existe entre 0,5 e 2,0 (Decreto 3.048/99, art. 202-A)."""
        with self.assertRaises(ValidationError):
            self.env.company.l10n_br_hr_fap = 2.5


class TestCprbNoHolerite(EncargosPatronaisCommon):
    """RF-33: reoneração gradual da CPRB no holerite."""

    def test_cprb_2026_reduz_somente_a_cpp(self):
        """2026: CPP a 10% (600), RAT e terceiros INTEGRAIS."""
        self._config_empresa(tax_framework="3", rat="3", cprb_optante=True)
        payslip = self._holerite()
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "CPP"), 600.00)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "RAT"), 180.00)
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "TERCEIROS"), 348.00)

    def test_cprb_2027_sobe_para_quinze_por_cento(self):
        """2027: proporção de 75% dos 20% -> 15% (900)."""
        self._config_empresa(tax_framework="3", rat="3", cprb_optante=True)
        payslip = self._holerite(date_from=date(2027, 3, 1), date_to=date(2027, 3, 31))
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "CPP"), 900.00)

    def test_cprb_2028_encerra_a_desoneracao(self):
        """2028: fim do regime, CPP integral mesmo para o optante."""
        self._config_empresa(tax_framework="3", rat="3", cprb_optante=True)
        payslip = self._holerite(date_from=date(2028, 3, 1), date_to=date(2028, 3, 31))
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "CPP"), 1200.00)

    def test_atividade_concomitante_proporcionaliza(self):
        """40% de receita não desonerada em 2026: 20% x 0,7 = 14% (840)."""
        self._config_empresa(
            tax_framework="3", rat="3", cprb_optante=True, perc_nao_desonerada=40.0
        )
        payslip = self._holerite()
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "CPP"), 840.00)

    def test_decimo_terceiro_dispensa_so_a_cpp(self):
        """13º de 2026 sem CPP, mas RAT e terceiros seguem integrais.

        A apuração do 13º vive no l10n_br_hr_vacation; aqui se prova a regra na
        fonte (o resolvedor de alíquotas da empresa), que é o que aquele módulo
        e o eSocial consomem.
        """
        company = self._config_empresa(tax_framework="3", rat="3", cprb_optante=True)
        aliq13 = company._l10n_br_hr_aliquotas_patronais(
            COMPETENCIA_FIM, decimo_terceiro=True
        )
        self.assertEqual(aliq13["cpp"], 0.0)
        self.assertAlmostEqual(aliq13["rat"], 0.03)
        self.assertAlmostEqual(aliq13["terceiros"], 0.058)
        # 2028: o 13º volta a ter CPP integral.
        aliq13_2028 = company._l10n_br_hr_aliquotas_patronais(
            date(2028, 12, 31), decimo_terceiro=True
        )
        self.assertAlmostEqual(aliq13_2028["cpp"], 0.20)

    def test_sem_vigencia_cadastrada_falha_alto(self):
        """Competência anterior à transição: erro explícito, nunca chute."""
        company = self._config_empresa(tax_framework="3", cprb_optante=True)
        with self.assertRaises(UserError):
            company._l10n_br_hr_aliquotas_patronais(date(2023, 5, 31))

    def test_nao_optante_nao_consulta_a_tabela(self):
        """Empresa fora do regime não pode falhar por falta de vigência CPRB."""
        company = self._config_empresa(tax_framework="3", cprb_optante=False)
        aliq = company._l10n_br_hr_aliquotas_patronais(date(2023, 5, 31))
        self.assertAlmostEqual(aliq["cpp"], 0.20)


class TestProvisoesNoHolerite(EncargosPatronaisCommon):
    """RF-34: provisões mensais de férias e 13º com encargos por regime."""

    def test_provisoes_com_encargo_cheio(self):
        """Regime normal: 666,67 + 238,67 de encargo; 500,00 + 179,00."""
        self._config_empresa(tax_framework="3", rat="2")
        payslip = self._holerite()
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "PROV_FERIAS"), 666.67
        )
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "PROV_FERIAS_ENC"), 238.67
        )
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "PROV_13"), 500.00)
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "PROV_13_ENC"), 179.00
        )

    def test_provisao_nao_afeta_o_liquido(self):
        """Provisão é custo por competência, não pagamento: NET intacto."""
        self._config_empresa(tax_framework="3", rat="2")
        payslip = self._holerite()
        liquido = self._get_line_total(payslip, "NET")
        inss = self._get_line_total(payslip, "INSS")
        irrf = self._get_line_total(payslip, "IRRF")
        self.assertAlmostEqualMoney(liquido, SALARIO - inss - irrf)
        self.assertGreater(self._get_line_total(payslip, "PROV_FERIAS"), 0.0)

    def test_provisao_no_simples_leva_so_fgts(self):
        """Simples anexo III: 8% de FGTS sobre a provisão, nada mais."""
        self._config_empresa(tax_framework="1", simples_anexo="iii")
        payslip = self._holerite()
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "PROV_FERIAS_ENC"), 53.33
        )
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "PROV_13_ENC"), 40.00)

    def test_ferias_indenizadas_esperadas_reduzem_o_encargo(self):
        """30% de indenização esperada: encargo sobre 70% da provisão."""
        self._config_empresa(tax_framework="3", rat="2", perc_ferias_indenizadas=30.0)
        payslip = self._holerite()
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "PROV_FERIAS_ENC"), 167.07
        )

    def test_provisao_13_de_optante_cprb_usa_a_coluna_do_13(self):
        """Sem CPP na provisão do 13º (2026), mas com RAT e terceiros."""
        self._config_empresa(tax_framework="3", rat="3", cprb_optante=True)
        payslip = self._holerite()
        # 500 x (0 + 3% + 5,8% + 8%) = 84,00
        self.assertAlmostEqualMoney(self._get_line_total(payslip, "PROV_13_ENC"), 84.00)
        # A provisão de férias continua com a CPP do mês (10% em 2026).
        # 666,67 x (10% + 3% + 5,8% + 8%) = 178,67
        self.assertAlmostEqualMoney(
            self._get_line_total(payslip, "PROV_FERIAS_ENC"), 178.67
        )
