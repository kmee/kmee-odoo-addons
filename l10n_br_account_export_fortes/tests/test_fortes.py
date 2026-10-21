# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.l10n_br_account_export.tests.layout_case import LayoutCase


@tagged("post_install", "-at_install")
class TestFortes(LayoutCase):
    """Contrato completo do chassi aplicado ao layout Fortes AG."""

    _layout = "fortes"
    _is_spreadsheet = False
    _fixed_width = None

    def test_cabecalho_e_detalhe(self):
        export = self._run()
        linhas = self._lines(export)
        self.assertTrue(linhas[0].startswith("0010"))
        self.assertTrue(linhas[1].startswith("1004"))
        self.assertTrue(export.attachment_ids[0].name.endswith(".CT"))
