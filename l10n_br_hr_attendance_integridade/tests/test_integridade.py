# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Testes da verificação de integridade do PTRP."""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..models import ptrp_escopo
from ..models.l10n_br_hr_ptrp_integridade import (
    PARAM_RESUMO_HOMOLOGADO,
    PARAM_VERSAO_ATESTADA,
)


@tagged("post_install", "-at_install")
class TestIntegridadePtrp(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.verificador = cls.env["l10n_br.hr.ptrp.integridade"]
        cls.parametro = cls.env["ir.config_parameter"].sudo()

    def test_resumo_e_estavel_entre_chamadas(self):
        """Sem alteração no código, o resumo tem que se repetir."""
        self.assertEqual(
            self.verificador.resumo_fonte(), self.verificador.resumo_fonte()
        )

    def test_resumo_tem_formato_sha256(self):
        resumo = self.verificador.resumo_fonte()
        self.assertEqual(len(resumo), 64)
        int(resumo, 16)

    def test_manifesto_cobre_o_nucleo_declarado(self):
        manifesto = dict(self.verificador._manifesto_fonte())
        for arquivo in (
            "l10n_br_hr_attendance/models/l10n_br_hr_marcacao.py",
            "l10n_br_hr_attendance_afd/models/afd_crc.py",
            "l10n_br_hr_attendance_apuracao/models/regras_jornada.py",
            "l10n_br_hr_attendance_aej/models/aej_layout.py",
        ):
            self.assertIn(arquivo, manifesto)
            self.assertEqual(len(manifesto[arquivo]), 64)

    def test_escopo_nao_inclui_views_nem_testes(self):
        """Mudar tela ou teste não pode obrigar a reemitir o atestado."""
        caminhos = [caminho for caminho, _resumo in self.verificador._manifesto_fonte()]
        self.assertFalse([c for c in caminhos if "/views/" in c])
        self.assertFalse([c for c in caminhos if "/tests/" in c])
        self.assertFalse([c for c in caminhos if "/i18n/" in c])
        self.assertFalse([c for c in caminhos if c.endswith("README.rst")])

    def test_alteracao_no_nucleo_muda_o_resumo(self):
        """O resumo precisa reagir a uma linha diferente no escopo."""
        entradas = self.verificador._manifesto_fonte()
        original = ptrp_escopo.resumo_do_manifesto(entradas)
        adulterado = [(caminho, resumo) for caminho, resumo in entradas]
        adulterado[0] = (adulterado[0][0], "0" * 64)
        self.assertNotEqual(ptrp_escopo.resumo_do_manifesto(adulterado), original)

    def test_ordem_dos_arquivos_nao_altera_o_resumo(self):
        """O texto canônico é ordenado: a ordem de leitura não pode importar."""
        entradas = self.verificador._manifesto_fonte()
        self.assertEqual(
            ptrp_escopo.resumo_do_manifesto(entradas),
            ptrp_escopo.resumo_do_manifesto(list(reversed(entradas))),
        )

    def test_sem_homologado_a_conferencia_fica_indefinida(self):
        self.parametro.set_param(PARAM_RESUMO_HOMOLOGADO, "")
        estado = self.verificador.verificar()
        self.assertIsNone(estado["confere"])
        self.assertIn(
            "Não há resumo homologado", self.verificador.texto_do_diagnostico()
        )

    def test_homologado_igual_confere(self):
        self.parametro.set_param(
            PARAM_RESUMO_HOMOLOGADO, self.verificador.resumo_fonte()
        )
        self.parametro.set_param(PARAM_VERSAO_ATESTADA, "16.0.1")
        estado = self.verificador.verificar()
        self.assertTrue(estado["confere"])
        self.assertIn(
            "confere com o homologado", self.verificador.texto_do_diagnostico()
        )

    def test_homologado_diferente_acusa_divergencia(self):
        self.parametro.set_param(PARAM_RESUMO_HOMOLOGADO, "f" * 64)
        estado = self.verificador.verificar()
        self.assertFalse(estado["confere"])
        self.assertIn("DIVERGE do homologado", self.verificador.texto_do_diagnostico())

    def test_acao_de_servidor_sobre_modelo_atestado_e_detectada(self):
        """Código em banco altera o resultado sem tocar em arquivo nenhum."""
        modelo = self.env["ir.model"]._get("l10n_br.hr.apuracao.dia")
        self.env["ir.actions.server"].create(
            {
                "name": "Ajuste silencioso de apuração",
                "model_id": modelo.id,
                "state": "code",
                "code": "records.write({'horas_extras': 0})",
            }
        )
        divergencias = self.verificador._codigo_em_banco()
        self.assertTrue(
            any("Ajuste silencioso" in item for item in divergencias), divergencias
        )
        self.assertIn("Ação de servidor", self.verificador.texto_do_diagnostico())

    def test_modulos_do_ptrp_nao_contam_como_extensao(self):
        """Os próprios módulos da suíte não podem aparecer como intrusos."""
        self.assertFalse(self.verificador._extensoes_de_terceiros())

    def test_manifesto_impresso_permite_recalcular(self):
        texto = self.verificador.imprimir_manifesto()
        linhas = texto.strip().split("\n")
        self.assertTrue(linhas[-1].startswith("resumo="))
        entradas = [
            tuple(linha.rsplit(":", 1)) for linha in linhas[:-2] if ":" in linha
        ]
        self.assertEqual(
            ptrp_escopo.resumo_do_manifesto(entradas),
            linhas[-1].split("=", 1)[1],
        )
