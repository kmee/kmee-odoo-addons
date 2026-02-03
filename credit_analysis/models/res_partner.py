# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_company_ids = fields.One2many(
        comodel_name="credit.company",
        inverse_name="partner_id",
        string="Empresas de Credito",
    )
    credit_company_count = fields.Integer(
        string="Consultas de Credito",
        compute="_compute_credit_company_count",
    )

    def _compute_credit_company_count(self):
        for partner in self:
            partner.credit_company_count = len(partner.credit_company_ids)

    def action_view_credit_companies(self):
        """View credit companies linked to this partner."""
        self.ensure_one()
        if self.credit_company_count == 1:
            return {
                "name": _("Empresa de Credito"),
                "type": "ir.actions.act_window",
                "res_model": "credit.company",
                "view_mode": "form",
                "res_id": self.credit_company_ids[0].id,
            }
        return {
            "name": _("Empresas de Credito"),
            "type": "ir.actions.act_window",
            "res_model": "credit.company",
            "view_mode": "tree,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
