# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.l10n_br_account_export.tests.layout_case import LayoutCase


@tagged("post_install", "-at_install")
class TestProtheus(LayoutCase):
    """Contrato completo do chassi aplicado ao layout TOTVS Protheus."""

    _layout = "protheus"
    _is_spreadsheet = False
    _fixed_width = 139

    def test_valor_em_centavos(self):
        export = self._run()
        self.assertIn("00000000000150000", self._lines(export)[0])
