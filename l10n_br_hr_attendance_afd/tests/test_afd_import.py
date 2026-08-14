# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Testes da importação de AFD no ORM (RP-05 a RP-08)."""

import base64

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..models import afd_layout
from . import fixtures


@tagged("post_install", "-at_install")
class TestAfdImport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rep = cls.env["l10n_br.hr.rep"].create(
            {
                "name": "REP-C da fábrica",
                "tipo": "rep_c",
                "numero_fabricacao": fixtures.NUMERO_FABRICACAO,
                "cnpj_cpf": fixtures.CNPJ_EMPREGADOR,
                "atestado_date_start": "2020-01-01",
                "atestado_date_end": "2099-12-31",
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Maria da Silva",
                "address_home_id": cls.env["res.partner"]
                .create(
                    {
                        "name": "Maria da Silva",
                        "vat": fixtures.CPF_EMPREGADO,
                        "country_id": cls.env.ref("base.br").id,
                    }
                )
                .id,
                "pis_pasep": fixtures.PIS_EMPREGADO,
                "tz": "America/Sao_Paulo",
            }
        )

    def _criar_import(self, conteudo, **extra):
        vals = {
            "name": "Importação de teste",
            "rep_id": self.rep.id,
            "arquivo": base64.b64encode(
                conteudo.encode(afd_layout.ENCODING_AFD, errors="replace")
            ),
            "arquivo_nome": "AFD.txt",
        }
        vals.update(extra)
        return self.env["l10n_br.hr.afd.import"].create(vals)

    def test_analise_nao_grava_marcacao(self):
        """Analisar é diagnóstico: nada entra na base antes da decisão."""
        importacao = self._criar_import(fixtures.afd_671())
        importacao.action_analisar()
        self.assertEqual(importacao.state, "analisado")
        self.assertEqual(importacao.qtd_marcacoes, 4)
        self.assertEqual(importacao.leiaute_detectado, "671")
        self.assertFalse(importacao.marcacao_ids)

    def test_importacao_cria_marcacoes_conciliadas(self):
        importacao = self._criar_import(fixtures.afd_671())
        importacao.action_importar()
        self.assertEqual(importacao.state, "importado")
        self.assertEqual(importacao.qtd_importadas, 4)
        self.assertEqual(importacao.qtd_pendentes, 0)
        self.assertEqual(
            set(importacao.marcacao_ids.mapped("employee_id")), {self.employee}
        )
        self.assertEqual(sorted(importacao.marcacao_ids.mapped("nsr")), [1, 2, 3, 4])

    def test_reimportacao_do_mesmo_arquivo_nao_duplica(self):
        """Idempotência (RP-08): NSR já existente é ignorado, não duplicado."""
        primeira = self._criar_import(fixtures.afd_671())
        primeira.action_importar()
        segunda = self._criar_import(fixtures.afd_671())
        segunda.action_importar()
        self.assertEqual(segunda.qtd_importadas, 0)
        self.assertEqual(segunda.qtd_duplicadas, 4)
        total = self.env["l10n_br.hr.marcacao"].search_count(
            [("rep_id", "=", self.rep.id)]
        )
        self.assertEqual(total, 4)

    def test_arquivo_estendido_importa_so_o_novo(self):
        """Coleta incremental: o relógio reenvia o histórico com o novo no fim."""
        self._criar_import(fixtures.afd_671()).action_importar()
        estendido = fixtures.afd_671(
            marcacoes=fixtures.marcacoes_671(horas=(11, 15, 16, 20))
            + fixtures.marcacoes_671(dia=3, horas=(11, 15), nsr_inicial=5)
        )
        segunda = self._criar_import(estendido)
        segunda.action_importar()
        self.assertEqual(segunda.qtd_importadas, 2)
        self.assertEqual(segunda.qtd_duplicadas, 4)

    def test_marcacao_sem_funcionario_fica_pendente(self):
        conteudo = fixtures.afd_671(marcacoes=fixtures.marcacoes_671(cpf="11122233396"))
        importacao = self._criar_import(conteudo)
        importacao.action_importar()
        self.assertEqual(importacao.qtd_pendentes, 4)
        self.assertEqual(importacao.qtd_importadas, 4)
        self.assertFalse(importacao.marcacao_ids.mapped("employee_id"))

    def test_reconciliacao_apos_cadastrar_documento(self):
        conteudo = fixtures.afd_671(marcacoes=fixtures.marcacoes_671(cpf="11122233396"))
        importacao = self._criar_import(conteudo)
        importacao.action_importar()
        # Cadastro sem endereço particular: o CPF vem do campo do próprio
        # funcionário, e a conciliação precisa enxergar essa fonte também.
        novo = self.env["hr.employee"].create(
            {"name": "João Recém-cadastrado", "cnpj_cpf": "111.222.333-96"}
        )
        conciliadas = importacao.action_reconciliar_pendentes()
        self.assertEqual(conciliadas, 4)
        self.assertEqual(importacao.qtd_pendentes, 0)
        self.assertEqual(set(importacao.marcacao_ids.mapped("employee_id")), {novo})

    def test_leiaute_1510_concilia_por_pis(self):
        importacao = self._criar_import(fixtures.afd_1510(), leiaute="1510")
        importacao.action_importar()
        self.assertEqual(importacao.leiaute_detectado, "1510")
        self.assertEqual(importacao.qtd_importadas, 4)
        self.assertEqual(importacao.qtd_pendentes, 0)
        self.assertEqual(
            set(importacao.marcacao_ids.mapped("employee_id")), {self.employee}
        )

    def test_lacuna_de_nsr_e_registrada(self):
        importacao = self._criar_import(fixtures.afd_671_com_lacuna())
        importacao.action_analisar()
        self.assertTrue(importacao.tem_lacuna)
        self.assertIn("NSR 3 a 4", importacao.lacunas_nsr)

    def test_crc_divergente_marca_erro_mas_permite_importar(self):
        """O operador decide: o arquivo pode ser o único registro existente."""
        importacao = self._criar_import(fixtures.afd_671_com_crc_invalido())
        importacao.action_analisar()
        self.assertEqual(importacao.state, "erro")
        self.assertIn("CRC-16 divergente", importacao.log)
        importacao.action_importar()
        self.assertEqual(importacao.qtd_importadas, 4)

    def test_contador_de_nsr_do_rep_acompanha_o_arquivo(self):
        importacao = self._criar_import(fixtures.afd_671())
        importacao.action_importar()
        self.assertEqual(self.rep.nsr_ultimo, 4)

    def test_exportacao_reproduz_as_marcacoes_importadas(self):
        """Ida e volta: o que foi importado tem que sair igual no AFD gerado."""
        importacao = self._criar_import(fixtures.afd_671())
        importacao.action_importar()
        nome, conteudo = self.rep.gerar_afd("2026-03-01", "2026-03-31")
        self.assertTrue(nome.startswith("AFD"))
        self.assertTrue(nome.endswith("REP_C.txt"))
        from ..models import afd_parser

        relido = afd_parser.ler_afd(conteudo)
        self.assertFalse(relido.ocorrencias, relido.ocorrencias)
        self.assertEqual(len(relido.marcacoes), 4)
        self.assertEqual(
            [m["nsr"] for m in relido.marcacoes],
            sorted(importacao.marcacao_ids.mapped("nsr")),
        )

    def test_wizard_de_exportacao_gera_anexo(self):
        self._criar_import(fixtures.afd_671()).action_importar()
        wizard = self.env["l10n_br.hr.afd.export.wizard"].create(
            {
                "rep_id": self.rep.id,
                "date_from": "2026-03-01",
                "date_to": "2026-03-31",
            }
        )
        wizard.action_gerar()
        self.assertTrue(wizard.arquivo)
        conteudo = base64.b64decode(wizard.arquivo).decode(afd_layout.ENCODING_AFD)
        self.assertIn(afd_layout.ASSINATURA_EM_ARQUIVO, conteudo)
