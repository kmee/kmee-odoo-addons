# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.l10n_br_account_export.tests.layout_case import LayoutCase


@tagged("post_install", "-at_install")
class TestAlterdata(LayoutCase):
    """Contrato completo do chassi aplicado ao layout Alterdata (WCont)."""

    _layout = "alterdata"
    _is_spreadsheet = False
    _fixed_width = None

    def test_usa_aspas_e_virgula(self):
        export = self._run()
        texto = self._text(export)
        self.assertTrue(self._lines(export)[0].startswith('""'))
        self.assertIn('"05/08/2026"', texto)
        self.assertIn('"1500,00"', texto)
