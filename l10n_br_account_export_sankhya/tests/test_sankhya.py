# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.l10n_br_account_export.tests.layout_case import LayoutCase


@tagged("post_install", "-at_install")
class TestSankhya(LayoutCase):
    """Contrato completo do chassi aplicado ao layout Sankhya."""

    _layout = "sankhya"
    _is_spreadsheet = True
    _fixed_width = None
