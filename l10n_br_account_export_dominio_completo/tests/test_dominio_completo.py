# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.l10n_br_account_export.tests.layout_case import LayoutCase


@tagged("post_install", "-at_install")
class TestDominioCompleto(LayoutCase):
    """Contrato completo do chassi aplicado ao layout Dominio com plano de contas."""

    _layout = "dominio_completo"
    _is_spreadsheet = False
    _fixed_width = None

    def test_entrega_tambem_o_plano_de_contas(self):
        """A variante completa manda o registro 0200 das contas usadas.

        E o que costuma garantir importacao sem ajuste manual: as contas passam
        a existir no destino.
        """
        export = self._run()
        self.assertEqual(len(export.attachment_ids), 2)
        plano = self._text(export, 1)
        self.assertIn("|0200|", plano)
        self.assertIn("1101", plano)
        self.assertIn("2201", plano)
