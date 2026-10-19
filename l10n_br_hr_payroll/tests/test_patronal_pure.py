# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes unitários puros dos encargos patronais e das provisões (RF-31 a RF-34).

Sem ORM: exercitam diretamente as funções de ``salary_rules_br`` que decidem
QUAIS encargos são devidos em cada regime tributário e quanto vale a provisão.
"""
from odoo.tests.common import BaseCase

from odoo.addons.l10n_br_hr_payroll.models.salary_rules_br import (
    aliquota_cpp_cprb,
    aliquota_rat_ajustado,
    aliquotas_patronais,
    calc_encargos_sobre_provisao,
    calc_provisao_decimo_terceiro,
    calc_provisao_ferias,
)

# Parâmetros do cenário de conferência: salário de R$ 6.000,00, RAT 2% (risco
# médio), FAP neutro e terceiros de 5,8% (FPAS 507/515).
SALARIO = 6000.0
RAT = 2.0
FAP = 1.0
TERCEIROS = 5.8


class TestRatAjustado(BaseCase):
    """RAT ajustado = RAT x FAP (Lei 8.212/91 art. 22 II + Dec. 3.048/99 202-A)."""

    def test_fap_neutro_mantem_rat(self):
        self.assertEqual(aliquota_rat_ajustado(3.0, 1.0), 3.0)

    def test_fap_reduz_ao_minimo(self):
        self.assertEqual(aliquota_rat_ajustado(2.0, 0.5), 1.0)

    def test_fap_maximo_dobra(self):
        self.assertEqual(aliquota_rat_ajustado(3.0, 2.0), 6.0)

    def test_fap_com_quatro_casas(self):
        """O FAP é publicado com 4 casas; o ajustado preserva a precisão."""
        self.assertEqual(aliquota_rat_ajustado(3.0, 0.7639), 2.2917)


class TestAliquotasPorRegime(BaseCase):
    """Quais encargos cada regime tributário gera (RF-32)."""

    def _aliquotas(self, tax_framework="3", simples_anexo=False, **kw):
        return aliquotas_patronais(
            tax_framework=tax_framework,
            simples_anexo=simples_anexo,
            rat=RAT,
            fap=FAP,
            perc_terceiros=TERCEIROS,
            **kw,
        )

    def test_regime_normal_encargo_cheio(self):
        """Lucro Real/Presumido: CPP 20% + RAT ajustado + terceiros + FGTS."""
        aliq = self._aliquotas()
        self.assertAlmostEqual(aliq["cpp"], 0.20)
        self.assertAlmostEqual(aliq["rat"], 0.02)
        self.assertAlmostEqual(aliq["terceiros"], 0.058)
        self.assertAlmostEqual(aliq["fgts"], 0.08)
        self.assertAlmostEqual(aliq["total_patronal"], 0.278)
        self.assertAlmostEqual(aliq["total_com_fgts"], 0.358)
        # Conferência em reais sobre R$ 6.000,00.
        self.assertAlmostEqual(SALARIO * aliq["cpp"], 1200.0)
        self.assertAlmostEqual(SALARIO * aliq["rat"], 120.0)
        self.assertAlmostEqual(SALARIO * aliq["terceiros"], 348.0)

    def test_simples_anexo_iii_somente_fgts(self):
        """Simples I/II/III/V: nada de CPP, RAT ou terceiros (LC 123 art. 13)."""
        for anexo in ("i", "ii", "iii", "v"):
            aliq = self._aliquotas(tax_framework="1", simples_anexo=anexo)
            self.assertEqual(aliq["cpp"], 0.0, "anexo %s não deve ter CPP" % anexo)
            self.assertEqual(aliq["rat"], 0.0, "anexo %s não deve ter RAT" % anexo)
            self.assertEqual(aliq["terceiros"], 0.0)
            self.assertAlmostEqual(aliq["fgts"], 0.08)
            self.assertEqual(aliq["total_patronal"], 0.0)

    def test_simples_sem_anexo_informado_nao_gera_patronal(self):
        """Optante sem anexo cadastrado: o padrão é a CPP estar no DAS."""
        aliq = self._aliquotas(tax_framework="1")
        self.assertEqual(aliq["total_patronal"], 0.0)

    def test_simples_mei_e_sublimite_seguem_o_simples(self):
        for framework in ("2", "4"):
            aliq = self._aliquotas(tax_framework=framework, simples_anexo="iii")
            self.assertEqual(aliq["total_patronal"], 0.0)

    def test_simples_anexo_iv_cpp_e_rat_sem_terceiros(self):
        """Anexo IV: CPP e RAT por fora (art. 18 §5º-C), terceiros dispensados."""
        aliq = self._aliquotas(tax_framework="1", simples_anexo="iv")
        self.assertAlmostEqual(aliq["cpp"], 0.20)
        self.assertAlmostEqual(aliq["rat"], 0.02)
        self.assertEqual(
            aliq["terceiros"],
            0.0,
            "terceiros são dispensados em TODO o Simples (LC 123 art. 13 §3º)",
        )
        self.assertAlmostEqual(SALARIO * aliq["cpp"], 1200.0)
        self.assertAlmostEqual(SALARIO * aliq["rat"], 120.0)

    def test_aprendiz_fgts_dois_por_cento(self):
        aliq = self._aliquotas(aprendiz=True)
        self.assertAlmostEqual(aliq["fgts"], 0.02)


class TestCprb(BaseCase):
    """Reoneração gradual da CPRB (Lei 14.973/2024) - RF-33."""

    def test_direcao_do_perc_red_contrib(self):
        """percRedContrib é a receita NÃO desonerada: 0 = desoneração total.

        Este é o erro clássico da reoneração: informar 100 para "totalmente
        desonerada" inverte o cálculo e a CPP sai integral.
        """
        # 2026: proporção de 50% dos 20% -> 10% efetivos.
        self.assertAlmostEqual(aliquota_cpp_cprb(50.0, 0.0), 0.10)
        # Nada desonerado no mês: CPP integral.
        self.assertAlmostEqual(aliquota_cpp_cprb(50.0, 100.0), 0.20)

    def test_cronograma_da_transicao(self):
        """Proporções de 2024 a 2028 sobre folha totalmente desonerada."""
        self.assertAlmostEqual(aliquota_cpp_cprb(0.0, 0.0), 0.0)  # 2024
        self.assertAlmostEqual(aliquota_cpp_cprb(25.0, 0.0), 0.05)  # 2025
        self.assertAlmostEqual(aliquota_cpp_cprb(50.0, 0.0), 0.10)  # 2026
        self.assertAlmostEqual(aliquota_cpp_cprb(75.0, 0.0), 0.15)  # 2027
        self.assertAlmostEqual(aliquota_cpp_cprb(100.0, 0.0), 0.20)  # 2028+

    def test_atividade_concomitante_proporcional(self):
        """40% da receita não desonerada em 2026: 20% x (0,4 + 0,5 x 0,6)."""
        self.assertAlmostEqual(aliquota_cpp_cprb(50.0, 40.0), 0.14)
        self.assertAlmostEqual(SALARIO * aliquota_cpp_cprb(50.0, 40.0), 840.0)

    def test_rat_e_terceiros_ficam_integrais(self):
        """Armadilha central: a proporção alcança SÓ os incisos I e III."""
        aliq = aliquotas_patronais(
            tax_framework="3",
            rat=3.0,
            fap=FAP,
            perc_terceiros=TERCEIROS,
            cprb_perc_cpp=50.0,
            cprb_perc_contrib_nao_desonerada=0.0,
        )
        self.assertAlmostEqual(aliq["cpp"], 0.10)
        self.assertAlmostEqual(aliq["rat"], 0.03, msg="RAT não é reduzido pela CPRB")
        self.assertAlmostEqual(
            aliq["terceiros"], 0.058, msg="terceiros não são reduzidos pela CPRB"
        )
        self.assertAlmostEqual(SALARIO * aliq["cpp"], 600.0)
        self.assertAlmostEqual(SALARIO * aliq["rat"], 180.0)
        self.assertAlmostEqual(SALARIO * aliq["terceiros"], 348.0)

    def test_nao_optante_ignora_cronograma(self):
        """Sem opção pela CPRB (``None``) a CPP é integral, sem consultar ano."""
        aliq = aliquotas_patronais(
            tax_framework="3", rat=RAT, fap=FAP, perc_terceiros=TERCEIROS
        )
        self.assertAlmostEqual(aliq["cpp"], 0.20)


class TestProvisoes(BaseCase):
    """Provisões mensais de férias e 13º com encargos (RF-34)."""

    def test_provisao_ferias_inclui_um_terco(self):
        """1/12 + 1/3 = remuneração x 4 / 36."""
        self.assertAlmostEqual(calc_provisao_ferias(SALARIO), 666.67)

    def test_provisao_decimo_terceiro_um_doze_avos(self):
        self.assertAlmostEqual(calc_provisao_decimo_terceiro(SALARIO), 500.0)

    def test_encargos_sobre_provisao_regime_normal(self):
        """Encargo cheio (CPP + RAT + terceiros + FGTS) sobre a provisão."""
        aliq = aliquotas_patronais(
            tax_framework="3", rat=RAT, fap=FAP, perc_terceiros=TERCEIROS
        )
        provisao = calc_provisao_ferias(SALARIO)
        self.assertAlmostEqual(
            calc_encargos_sobre_provisao(provisao, aliq["total_com_fgts"]), 238.67
        )

    def test_encargos_sobre_provisao_simples_somente_fgts(self):
        """Simples anexo III: a provisão leva apenas o FGTS."""
        aliq = aliquotas_patronais(
            tax_framework="1",
            simples_anexo="iii",
            rat=RAT,
            fap=FAP,
            perc_terceiros=TERCEIROS,
        )
        provisao = calc_provisao_ferias(SALARIO)
        self.assertAlmostEqual(
            calc_encargos_sobre_provisao(provisao, aliq["total_com_fgts"]),
            53.33,
            msg="8% de FGTS sobre 666,67",
        )

    def test_ferias_indenizadas_saem_da_base_dos_encargos(self):
        """Férias indenizadas não têm INSS nem FGTS: 30% esperados de indenização."""
        aliq = aliquotas_patronais(
            tax_framework="3", rat=RAT, fap=FAP, perc_terceiros=TERCEIROS
        )
        provisao = calc_provisao_ferias(SALARIO)
        cheio = calc_encargos_sobre_provisao(provisao, aliq["total_com_fgts"])
        segregado = calc_encargos_sobre_provisao(
            provisao, aliq["total_com_fgts"], perc_base_isenta=30.0
        )
        self.assertAlmostEqual(segregado, 167.07)
        self.assertLess(segregado, cheio)
