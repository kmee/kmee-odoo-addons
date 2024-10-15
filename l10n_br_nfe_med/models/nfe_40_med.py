# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class Nfe40Med(models.AbstractModel):
    _inherit = "nfe.40.med"

    _rec_name = "nfe40_cProdANVISA"

    @api.depends("nfe40_cProdANVISA", "nfe40_xMotivoIsencao", "nfe40_vPMC")
    def _compute_display_name(self):
        super()._compute_display_name()

    def name_get(self):
        res = []
        for record in self:
            name = record.nfe40_cProdANVISA
            if record.nfe40_xMotivoIsencao:
                name += " - " + record.nfe40_xMotivoIsencao
            if record.nfe40_vPMC:
                name += " - " + record.nfe40_vPMC
            res.append((record.id, name))
        return res
