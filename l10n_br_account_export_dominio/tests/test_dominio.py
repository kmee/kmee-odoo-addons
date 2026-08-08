# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.l10n_br_account_export.tests.layout_case import LayoutCase


@tagged("post_install", "-at_install")
class TestDominio(LayoutCase):
    """Contrato completo do chassi aplicado ao layout Dominio (Thomson Reuters)."""

    _layout = "dominio"
    _is_spreadsheet = False
    _fixed_width = None

    def test_registros_e_bordas(self):
        """Conferido campo a campo contra arquivo real gerado pelo Dominio."""
        export = self._run()
        linhas = self._lines(export)

        self.assertEqual(len(linhas), 3, "0000 + 6000 + um 6100")
        for linha in linhas:
            self.assertTrue(linha.startswith("|"), linha)
            self.assertTrue(linha.endswith("|"), linha)

        self.assertEqual(linhas[0].split("|")[1], "0000")
        self.assertEqual(linhas[0].split("|")[2], "12345678000195")
        self.assertEqual(linhas[1].split("|")[1], "6000")
        self.assertEqual(linhas[1].split("|")[2], "X")

    def test_debito_e_credito_na_mesma_linha(self):
        """O 6100 do Dominio traz os dois lados no mesmo registro."""
        export = self._run()
        campos = self._lines(export)[2].split("|")
        self.assertEqual(campos[1], "6100")
        self.assertEqual(campos[2], "05/08/2026")
        self.assertEqual(campos[3], "1101")
        self.assertEqual(campos[4], "2201")
        self.assertEqual(campos[5], "1500,00")

    def test_rateio_usa_conta_zero(self):
        """Sem par unico, o layout detalha um lado e zera o outro."""
        multi = self._create_multi_move()
        export = self._create_export("dominio", multi)
        export.action_generate()
        partidas = [
            line.split("|")
            for line in self._lines(export)
            if line.split("|")[1] == "6100"
        ]
        self.assertEqual(len(partidas), 3)
        self.assertEqual(len([c for c in partidas if c[4] == "0"]), 2)
        self.assertEqual(len([c for c in partidas if c[3] == "0"]), 1)
