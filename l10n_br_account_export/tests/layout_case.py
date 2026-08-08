# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Contrato que todo layout precisa cumprir.

Cada modulo de layout herda esta classe e informa apenas o seu ``_layout``.
Assim um adapter novo ja nasce com a bateria completa, e uma regra nova vale
para todos os layouts de uma vez, sem copiar teste.
"""

from odoo.tests import tagged

from .common import AccountExportCommon


@tagged("post_install", "-at_install")
class LayoutCase(AccountExportCommon):
    _layout = None  # o modulo de layout preenche
    _is_spreadsheet = False
    _fixed_width = None  # largura da linha, para layouts posicionais

    def _run(self, moves=None, partial=False):
        export = self._create_export(self._layout, moves or self.move, partial)
        export.action_generate()
        return export

    def test_gera_arquivo(self):
        if not self._layout:
            self.skipTest("classe base")
        export = self._run()
        self.assertEqual(export.state, "done")
        self.assertTrue(export.attachment_ids)
        self.assertTrue(export.attachment_ids[0].raw)

    def test_deterministico(self):
        """Mesma entrada e mesma configuracao produzem bytes identicos."""
        if not self._layout:
            self.skipTest("classe base")
        export = self._run()
        conteudo = export.attachment_ids[0].raw
        export.action_back_to_draft()
        self.move.write({"l10n_br_account_export_id": export.id})
        export.action_generate()
        self.assertEqual(conteudo, export.attachment_ids[0].raw)

    def test_acento_sobrevive_ao_encoding(self):
        """Historico com acento nao pode quebrar a gravacao em ANSI."""
        if not self._layout:
            self.skipTest("classe base")
        self.move.button_draft()
        self.move.line_ids[0].name = "Emprestimo ção áé çü"
        self.move.action_post()
        export = self._run()
        self.assertTrue(export.attachment_ids[0].raw)

    def test_separador_e_quebra_nao_vazam(self):
        """Separador ou quebra de linha no historico corromperia o registro."""
        if not self._layout or self._is_spreadsheet:
            self.skipTest("nao se aplica")
        self.move.button_draft()
        self.move.line_ids[0].name = "Nota|123;com,tudo\ne quebra"
        self.move.action_post()
        export = self._run()
        texto = self._text(export)
        linhas = [line for line in texto.split("\n") if line]
        # a quebra do historico nao pode ter virado uma linha a mais
        self.assertTrue(
            all("e quebra" not in line or "Nota" in line for line in linhas)
        )

    def test_partidas_multiplas(self):
        """Lancamento rateado (dois debitos, um credito) nao pode quebrar."""
        if not self._layout:
            self.skipTest("classe base")
        multi = self._create_multi_move()
        export = self._create_export(self._layout, multi)
        export.action_generate()
        self.assertTrue(export.attachment_ids[0].raw)

    def test_largura_fixa(self):
        """Em layout posicional, toda linha tem a largura do contrato."""
        if not self._layout or not self._fixed_width:
            self.skipTest("nao e posicional")
        export = self._run()
        for linha in self._lines(export):
            self.assertEqual(
                len(linha), self._fixed_width, f"{self._layout}: {linha[:40]}"
            )

    def test_conta_sem_depara_bloqueia(self):
        """Sem codigo no plano do escritorio, o arquivo nao sai."""
        if not self._layout:
            self.skipTest("classe base")
        from odoo.exceptions import UserError

        move = self._create_move(
            "2026-08-07", 300.0, account_debito=self.account_sem_depara
        )
        export = self._create_export(self._layout, move)
        with self.assertRaises(UserError):
            export.action_generate()
        self.assertEqual(export.state, "draft")
