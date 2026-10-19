# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Testes do parser e do gerador de AFD (RP-05, RP-06, RP-08)."""

from datetime import datetime

from odoo.tests.common import BaseCase

from ..models import afd_layout, afd_parser
from . import fixtures


class TestAfdParser(BaseCase):
    def test_tamanhos_do_leiaute_671(self):
        """Confere as posições do Anexo V registro a registro."""
        self.assertEqual(afd_layout.tamanho_registro("671", "1"), 302)
        self.assertEqual(afd_layout.tamanho_registro("671", "2"), 331)
        self.assertEqual(afd_layout.tamanho_registro("671", "3"), 50)
        self.assertEqual(afd_layout.tamanho_registro("671", "4"), 73)
        self.assertEqual(afd_layout.tamanho_registro("671", "5"), 118)
        self.assertEqual(afd_layout.tamanho_registro("671", "6"), 36)
        self.assertEqual(afd_layout.tamanho_registro("671", "7"), 137)
        self.assertEqual(afd_layout.tamanho_registro("671", "9"), 64)

    def test_round_trip_671(self):
        conteudo = fixtures.afd_671()
        resultado = afd_parser.ler_afd(conteudo)
        self.assertEqual(resultado.leiaute, "671")
        self.assertFalse(resultado.ocorrencias, resultado.ocorrencias)
        self.assertEqual(len(resultado.marcacoes), 4)
        self.assertEqual(resultado.marcacoes[0]["nsr"], 1)
        self.assertEqual(resultado.marcacoes[0]["cpf"], fixtures.CPF_EMPREGADO)
        self.assertEqual(
            resultado.marcacoes[0]["datetime_marcacao"], datetime(2026, 3, 2, 11, 0)
        )

    def test_fuso_do_arquivo_e_respeitado(self):
        """08h em Brasília tem que virar 11h UTC, não 08h UTC."""
        conteudo = fixtures.afd_671()
        linha_marcacao = conteudo.split(afd_layout.TERMINADOR_LINHA)[1]
        self.assertIn("2026-03-02T08:00:00-0300", linha_marcacao)
        resultado = afd_parser.ler_afd(conteudo)
        self.assertEqual(resultado.marcacoes[0]["datetime_marcacao"].hour, 11)

    def test_cabecalho_lido(self):
        resultado = afd_parser.ler_afd(fixtures.afd_671())
        self.assertEqual(
            resultado.cabecalho["cnpj_cpf_empregador"], fixtures.CNPJ_EMPREGADOR
        )
        self.assertEqual(resultado.cabecalho["versao_leiaute"], "003")
        self.assertEqual(
            resultado.cabecalho["identificador_rep"], fixtures.NUMERO_FABRICACAO
        )

    def test_assinatura_em_arquivo_reconhecida(self):
        resultado = afd_parser.ler_afd(fixtures.afd_671())
        self.assertEqual(resultado.assinatura, afd_layout.ASSINATURA_EM_ARQUIVO)

    def test_crc_invalido_vira_ocorrencia_sem_parar_a_leitura(self):
        resultado = afd_parser.ler_afd(fixtures.afd_671_com_crc_invalido())
        codigos = [o.codigo for o in resultado.ocorrencias]
        self.assertIn("crc", codigos)
        self.assertTrue(resultado.tem_erro)
        # A marcação continua sendo lida: descartá-la seria perder jornada.
        self.assertEqual(len(resultado.marcacoes), 4)

    def test_lacuna_de_nsr_detectada(self):
        resultado = afd_parser.ler_afd(fixtures.afd_671_com_lacuna())
        self.assertEqual(resultado.lacunas_nsr, [(3, 4)])

    def test_trailer_divergente_vira_ocorrencia(self):
        conteudo = fixtures.afd_671()
        linhas = conteudo.split(afd_layout.TERMINADOR_LINHA)
        trailer = linhas[5]
        # Declara 9 marcações tipo 3 onde só existem 4.
        linhas[5] = trailer[:9] + trailer[9:18] + "000000009" + trailer[27:]
        resultado = afd_parser.ler_afd(afd_layout.TERMINADOR_LINHA.join(linhas))
        self.assertIn("trailer", [o.codigo for o in resultado.ocorrencias])

    def test_leiaute_1510_detectado_e_lido(self):
        conteudo = fixtures.afd_1510()
        resultado = afd_parser.ler_afd(conteudo)
        self.assertEqual(resultado.leiaute, "1510")
        self.assertEqual(len(resultado.marcacoes), 4)
        self.assertEqual(resultado.marcacoes[0]["pis"], fixtures.PIS_EMPREGADO)
        # 08h locais em Brasília (fuso -3) = 11h UTC.
        self.assertEqual(
            resultado.marcacoes[0]["datetime_marcacao"], datetime(2026, 3, 2, 11, 0)
        )

    def test_1510_respeita_fuso_informado(self):
        """Manaus (-4) não pode ser lido como Brasília (-3)."""
        resultado = afd_parser.ler_afd(fixtures.afd_1510(), fuso_horas=-4)
        self.assertEqual(
            resultado.marcacoes[0]["datetime_marcacao"], datetime(2026, 3, 2, 12, 0)
        )

    def test_data_hora_invalida_nao_derruba_o_arquivo(self):
        conteudo = fixtures.afd_671()
        linhas = conteudo.split(afd_layout.TERMINADOR_LINHA)
        linhas[1] = linhas[1][:10] + "2026-13-45T99:99:00-0300" + linhas[1][34:]
        resultado = afd_parser.ler_afd(afd_layout.TERMINADOR_LINHA.join(linhas))
        self.assertIn("conteudo", [o.codigo for o in resultado.ocorrencias])
        self.assertEqual(len(resultado.marcacoes), 3)

    def test_registro_tipo_7_com_hash(self):
        marcacoes = [
            {
                "nsr": 1,
                "tipo_registro": "7",
                "datetime_marcacao": datetime(2026, 3, 2, 11, 0),
                "datetime_gravacao": datetime(2026, 3, 2, 11, 1),
                "cpf": fixtures.CPF_EMPREGADO,
                "coletor": "02",
                "offline": False,
                "hash_registro": "a" * 64,
            }
        ]
        conteudo = afd_parser.gerar_afd(fixtures.cabecalho_671(), marcacoes)
        resultado = afd_parser.ler_afd(conteudo)
        self.assertFalse(resultado.ocorrencias, resultado.ocorrencias)
        lida = resultado.marcacoes[0]
        self.assertEqual(lida["tipo_registro"], "7")
        self.assertEqual(lida["hash_registro"], "a" * 64)
        self.assertEqual(lida["coletor"], "02")
        self.assertFalse(lida["offline"])
        self.assertEqual(resultado.trailer["qtd_tipo_7"], 1)

    def test_nome_do_arquivo_segue_o_anexo_v(self):
        self.assertEqual(
            afd_parser.nome_arquivo_afd("rep_c", "123", "12345678000195"),
            "AFD12312345678000195REP_C.txt",
        )
        self.assertEqual(
            afd_parser.nome_arquivo_afd("rep_p", "BR51", "12345678000195"),
            "AFDBR5112345678000195REP_P.txt",
        )
        self.assertEqual(
            afd_parser.nome_arquivo_afd("rep_a", "", "12345678000195"),
            "AFD12345678000195REP_A.txt",
        )

    def test_linhas_terminam_em_crlf(self):
        """Item 3 do Anexo V: cada linha termina com CR e LF."""
        conteudo = fixtures.afd_671()
        self.assertTrue(conteudo.endswith("\r\n"))
        self.assertNotIn("\n\n", conteudo)

    def test_arquivo_codifica_em_iso_8859_1(self):
        conteudo = afd_parser.gerar_afd(
            dict(fixtures.cabecalho_671(), razao_social="AÇÚCAR E CIA LTDA"),
            fixtures.marcacoes_671(),
        )
        bruto = conteudo.encode(afd_layout.ENCODING_AFD)
        self.assertIn("AÇÚCAR", bruto.decode(afd_layout.ENCODING_AFD))
