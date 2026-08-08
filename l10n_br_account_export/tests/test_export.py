# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import AccountExportCommon


@tagged("post_install", "-at_install")
class TestAccountExport(AccountExportCommon):
    """Comportamento do lote, independente de layout.

    Usa um layout de teste registrado na propria classe, para que o chassi seja
    testado sem depender do modulo de layouts.
    """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        # registra um layout minimo so para os testes do chassi
        cls.env["l10n_br.account.export.config"]._fields["layout"].selection.append(
            ("teste", "Layout de teste")
        )

    def _export_teste(self, moves=None, partial=False):
        export = self._create_export("teste", moves=moves, partial=partial)
        return export

    def test_layout_nao_implementado_avisa(self):
        """Sem adapter para o layout, o erro precisa ser claro."""
        export = self._export_teste(self.move)
        with self.assertRaises(UserError) as cm:
            export.action_generate()
        self.assertIn("nao esta implementado", str(cm.exception))

    def test_busca_de_lancamentos_respeita_periodo(self):
        fora = self._create_move("2026-09-10", 100.0)
        export = self._export_teste()
        export.action_get_moves()
        self.assertIn(self.move, export.move_ids)
        self.assertNotIn(fora, export.move_ids)

    def test_lancamento_exportado_nao_entra_em_novo_lote(self):
        """O vinculo com o lote e o que impede enviar duas vezes."""
        primeiro = self._export_teste()
        primeiro.action_get_moves()
        self.assertTrue(self.move.l10n_br_account_export_id)

        segundo = self._export_teste()
        with self.assertRaises(UserError):
            segundo.action_get_moves()

    def test_voltar_para_rascunho_libera_lancamentos(self):
        export = self._export_teste(self.move)
        export.state = "done"
        export.action_back_to_draft()
        self.assertEqual(export.state, "draft")
        self.assertFalse(self.move.l10n_br_account_export_id)

    def test_conta_sem_depara_gera_critica(self):
        move = self._create_move(
            "2026-08-07", 300.0, account_debito=self.account_sem_depara
        )
        export = self._export_teste(move)
        criticas = export._validate_export()
        self.assertTrue(criticas)
        self.assertIn("sem codigo no sistema do escritorio", criticas[0])

    def test_exportacao_parcial_solta_o_invalido(self):
        move_invalido = self._create_move(
            "2026-08-07", 300.0, account_debito=self.account_sem_depara
        )
        export = self._export_teste(self.move | move_invalido, partial=True)
        export._drop_invalid_moves()
        self.assertIn(self.move, export.move_ids)
        self.assertNotIn(move_invalido, export.move_ids)
        self.assertFalse(move_invalido.l10n_br_account_export_id)

    def test_nao_apaga_lote_gerado(self):
        export = self._export_teste(self.move)
        export.state = "done"
        with self.assertRaises(UserError):
            export.unlink()

    def test_aviso_de_periodo_ja_exportado(self):
        """Reexportar e permitido; o lote so avisa sobre a remessa anterior."""
        primeiro = self._export_teste(self.move)
        primeiro.state = "done"

        segundo = self._export_teste()
        anteriores = segundo._previous_exports()
        self.assertIn(primeiro, anteriores)

    def test_nome_de_arquivo_estavel(self):
        """Mesma entrada gera o mesmo nome: exigencia de determinismo."""
        export = self._export_teste(self.move)
        self.assertEqual(export._file_name(), "teste_202608.txt")
        self.assertEqual(
            export._file_name(sufixo="contas", extensao="csv"),
            "teste_202608_contas.csv",
        )

    def test_linhas_de_secao_ficam_fora(self):
        """Linha de secao e anotacao nao sao partidas contabeis."""
        export = self._export_teste(self.move)
        self.assertEqual(len(export._get_export_lines()), 2)
