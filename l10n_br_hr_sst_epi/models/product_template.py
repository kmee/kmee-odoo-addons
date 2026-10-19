# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_br_sst_ca_id = fields.Many2one(
        "l10n_br.sst.ca",
        string="Certificado de Aprovação",
        help="CA do equipamento. A validade é do certificado, não da entrega.",
    )
    l10n_br_sst_ca_state = fields.Selection(
        related="l10n_br_sst_ca_id.state",
        string="Situação do CA",
        readonly=True,
    )
    l10n_br_sst_ca_validade = fields.Date(
        related="l10n_br_sst_ca_id.validade",
        string="Validade do CA",
        readonly=True,
    )

    @api.onchange("l10n_br_sst_ca_id")
    def _onchange_l10n_br_sst_ca_id(self):
        """EPI com CA é, por definição, equipamento de proteção individual."""
        if self.l10n_br_sst_ca_id:
            self.is_ppe = True
            self.is_personal_equipment = True
