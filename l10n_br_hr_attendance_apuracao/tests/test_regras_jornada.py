# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Testes das regras puras de jornada (RP-10 a RP-14).

Sem ORM: entram ``datetime``, saem números. É o nível em que as regras da CLT
são conferíveis contra o texto legal sem ruído de infraestrutura.
"""

from datetime import date, datetime

from odoo.tests.common import BaseCase

from ..models import regras_jornada as r


def _dt(dia, hora, minuto=0):
    return datetime(2026, 3, dia, hora, minuto)


class TestTolerancia(BaseCase):
    """Art. 58, § 1º da CLT e Súmula 366 do TST."""

    def test_variacao_dentro_do_limite_nao_gera_nada(self):
        self.assertEqual(r.aplica_tolerancia(480, 488), (0.0, 0.0))
        self.assertEqual(r.aplica_tolerancia(480, 472), (0.0, 0.0))

    def test_limite_exato_ainda_e_tolerado(self):
        self.assertEqual(r.aplica_tolerancia(480, 490), (0.0, 0.0))

    def test_acima_do_limite_computa_o_tempo_integral(self):
        """Súmula 366: passou de 10 minutos, conta tudo, não só o excedente."""
        extra, deficit = r.aplica_tolerancia(480, 492)
        self.assertEqual(extra, 12)
        self.assertEqual(deficit, 0.0)

    def test_deficit_acima_do_limite_computa_integral(self):
        extra, deficit = r.aplica_tolerancia(480, 465)
        self.assertEqual(extra, 0.0)
        self.assertEqual(deficit, 15)

    def test_limite_configuravel(self):
        self.assertEqual(r.aplica_tolerancia(480, 495, limite_diario=20), (0.0, 0.0))

    def test_tolerancia_por_marcacao(self):
        previstas = [_dt(2, 8), _dt(2, 12), _dt(2, 13), _dt(2, 17)]
        realizadas = [_dt(2, 8, 3), _dt(2, 12, 2), _dt(2, 13, 1), _dt(2, 17, 4)]
        self.assertTrue(
            r.variacao_dentro_da_tolerancia_por_marcacao(previstas, realizadas)
        )

    def test_marcacao_isolada_acima_de_cinco_minutos(self):
        previstas = [_dt(2, 8), _dt(2, 17)]
        realizadas = [_dt(2, 8, 7), _dt(2, 17)]
        self.assertFalse(
            r.variacao_dentro_da_tolerancia_por_marcacao(previstas, realizadas)
        )


class TestPareamento(BaseCase):
    def test_quatro_marcacoes_viram_dois_pares(self):
        pares, impar = r.parear_marcacoes(
            [_dt(2, 8), _dt(2, 12), _dt(2, 13), _dt(2, 17)]
        )
        self.assertEqual(len(pares), 2)
        self.assertIsNone(impar)

    def test_marcacao_impar_e_devolvida_e_nao_inventada(self):
        """Art. 74: o sistema não fabrica marcação para fechar o par."""
        pares, impar = r.parear_marcacoes([_dt(2, 8), _dt(2, 12), _dt(2, 13)])
        self.assertEqual(len(pares), 1)
        self.assertEqual(impar, _dt(2, 13))

    def test_ordem_de_entrada_nao_importa(self):
        pares, _impar = r.parear_marcacoes([_dt(2, 17), _dt(2, 8)])
        self.assertEqual(pares, [(_dt(2, 8), _dt(2, 17))])

    def test_minutos_trabalhados_e_intervalo(self):
        pares = [(_dt(2, 8), _dt(2, 12)), (_dt(2, 13), _dt(2, 17))]
        self.assertEqual(r.minutos_trabalhados(pares), 480)
        self.assertEqual(r.minutos_intervalo(pares), 60)


class TestAdicionalNoturno(BaseCase):
    """Art. 73 da CLT."""

    def test_jornada_diurna_nao_tem_noturno(self):
        self.assertEqual(r.minutos_noturnos([(_dt(2, 8), _dt(2, 17))]), 0)

    def test_trecho_apos_22h(self):
        self.assertEqual(r.minutos_noturnos([(_dt(2, 21), _dt(2, 23))]), 60)

    def test_jornada_que_cruza_a_meia_noite(self):
        """22h as 6h: sete horas noturnas (22h-5h)."""
        self.assertEqual(r.minutos_noturnos([(_dt(2, 22), _dt(3, 6))]), 420)

    def test_madrugada_antes_das_cinco(self):
        self.assertEqual(r.minutos_noturnos([(_dt(2, 2), _dt(2, 6))]), 180)

    def test_hora_reduzida_converte_sete_em_oito(self):
        """52min30s de relógio equivalem a uma hora de jornada."""
        self.assertAlmostEqual(r.horas_noturnas_computadas(420), 8.0, places=4)

    def test_sem_hora_reduzida_mantem_o_cronologico(self):
        self.assertAlmostEqual(
            r.horas_noturnas_computadas(420, usar_hora_reduzida=False), 7.0, places=4
        )


class TestIntrajornada(BaseCase):
    """Art. 71 e art. 611-A, III da CLT."""

    def test_jornada_ate_quatro_horas_nao_exige_intervalo(self):
        self.assertEqual(r.intrajornada_minima(240), 0)

    def test_jornada_de_quatro_a_seis_horas_exige_quinze_minutos(self):
        self.assertEqual(r.intrajornada_minima(300), 15)

    def test_jornada_acima_de_seis_horas_exige_uma_hora(self):
        self.assertEqual(r.intrajornada_minima(480), 60)

    def test_norma_coletiva_pode_reduzir_ate_trinta(self):
        self.assertEqual(r.intrajornada_minima(480, 30), 30)

    def test_reducao_abaixo_de_trinta_e_recusada(self):
        """Art. 611-A, III fixa o piso; abaixo disso a norma não vale."""
        self.assertEqual(r.intrajornada_minima(480, 15), 30)

    def test_periodo_suprimido_e_so_o_que_faltou(self):
        """Art. 71, § 4º pós-reforma: paga-se o suprimido, não o intervalo todo."""
        self.assertEqual(r.intrajornada_suprimida(480, 40), 20)

    def test_intervalo_completo_nao_gera_verba(self):
        self.assertEqual(r.intrajornada_suprimida(480, 60), 0)

    def test_intervalo_maior_que_o_devido_nao_gera_credito(self):
        self.assertEqual(r.intrajornada_suprimida(480, 90), 0)


class TestInterjornada(BaseCase):
    """Art. 66 da CLT."""

    def test_onze_horas_exatas_respeitam(self):
        self.assertTrue(r.interjornada_respeitada(_dt(2, 21), _dt(3, 8)))

    def test_menos_de_onze_horas_violam(self):
        self.assertFalse(r.interjornada_respeitada(_dt(2, 22), _dt(3, 8)))

    def test_sem_jornada_anterior_nao_ha_violacao(self):
        self.assertTrue(r.interjornada_respeitada(None, _dt(3, 8)))


class TestReflexos(BaseCase):
    def test_dsr_sobre_horas_extras(self):
        """Súmula 172 do TST: HE / dias úteis x dias de repouso."""
        self.assertAlmostEqual(r.dsr_sobre_horas_extras(300, 25, 5), 60.0, places=2)

    def test_dsr_sem_dias_uteis_nao_estoura(self):
        self.assertEqual(r.dsr_sobre_horas_extras(300, 0, 5), 0.0)

    def test_desconto_de_dsr_conta_semanas_nao_faltas(self):
        """Duas faltas na mesma semana derrubam um repouso, não dois."""
        duas_na_mesma_semana = [date(2026, 3, 2), date(2026, 3, 4)]
        self.assertEqual(r.semanas_com_falta(duas_na_mesma_semana), 1)
        self.assertEqual(
            r.desconto_dsr_por_falta(100.0, r.semanas_com_falta(duas_na_mesma_semana)),
            100.0,
        )

    def test_faltas_em_semanas_distintas_descontam_dois_repousos(self):
        duas_semanas = [date(2026, 3, 2), date(2026, 3, 10)]
        self.assertEqual(r.semanas_com_falta(duas_semanas), 2)
        self.assertEqual(
            r.desconto_dsr_por_falta(100.0, r.semanas_com_falta(duas_semanas)), 200.0
        )


class TestFaixasHorasExtras(BaseCase):
    def test_distribuicao_em_duas_faixas(self):
        faixas = [
            {"limite_minutos": 120, "multiplicador": 1.5},
            {"limite_minutos": None, "multiplicador": 2.0},
        ]
        self.assertEqual(
            r.classifica_horas_extras(180, faixas), [(120, 1.5), (60, 2.0)]
        )

    def test_extra_menor_que_a_primeira_faixa(self):
        faixas = [{"limite_minutos": 120, "multiplicador": 1.5}]
        self.assertEqual(r.classifica_horas_extras(45, faixas), [(45, 1.5)])

    def test_sem_extra_nao_distribui(self):
        faixas = [{"limite_minutos": None, "multiplicador": 1.5}]
        self.assertEqual(r.classifica_horas_extras(0, faixas), [])
