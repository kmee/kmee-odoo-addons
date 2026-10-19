# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountExportConfig(models.Model):
    _inherit = "l10n_br.account.export.config"

    layout = fields.Selection(
        selection_add=[("sankhya", "Sankhya")],
        ondelete={"sankhya": "cascade"},
    )
