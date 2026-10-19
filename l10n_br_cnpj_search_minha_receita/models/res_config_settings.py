# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"

    cnpj_provider = fields.Selection(
        selection_add=[("minhareceita", "Minha Receita")],
        ondelete={"minhareceita": "set default"},
    )
