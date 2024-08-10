# flake8: noqa: B950
# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class L10nBrDiMixin(models.AbstractModel):

    _name = "l10n_br_di.mixin"
    _description = "Declaração Importação Mixin"

    def _s_currency(self, siscomex_code):
        return self.env["res.currency"].search(
            [("siscomex_code", "=", siscomex_code)],
            limit=1,
        )
