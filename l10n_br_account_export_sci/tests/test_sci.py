# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.l10n_br_account_export.tests.layout_case import LayoutCase


@tagged("post_install", "-at_install")
class TestSci(LayoutCase):
    """Contrato completo do chassi aplicado ao layout SCI (Visual Sucessor / Unico)."""

    _layout = "sci"
    _is_spreadsheet = False
    _fixed_width = None

    def test_ponto_decimal_e_data_compacta(self):
        export = self._run()
        campos = self._lines(export)[0].split(",")
        self.assertEqual(campos[1], "20260805")
        self.assertEqual(campos[4], "1500.00")
