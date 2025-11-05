# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class ResPartner(models.Model):

    _inherit = "res.partner"

    settlement = fields.Selection(
        selection_add=[
            ("vinte_seis", _("26 até 25")),
        ],
        ondelete={"vinte_seis": "set default"},
    )
