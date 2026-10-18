from odoo import fields, models


class ResPartnerTier(models.Model):
    _name = "res.partner.tier"
    _description = "Customer Tier"
    _order = "sequence, id"

    name = fields.Char(required=True)
    description = fields.Text()
    sequence = fields.Integer(default=10)
    priority = fields.Selection(
        selection=[
            ("0", "Low"),
            ("1", "Medium"),
            ("2", "High"),
            ("3", "Very High"),
        ],
        default="1",
    )
    color = fields.Integer()
    partner_count = fields.Integer(string="Partners", compute="_compute_partner_count")

    def _compute_partner_count(self):
        for tier in self:
            tier.partner_count = self.env["res.partner"].search_count(
                [("tier_id", "=", tier.id)]
            )

    def action_view_partners(self):
        self.ensure_one()
        return {
            "name": "Partners",
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "res.partner",
            "domain": [("tier_id", "=", self.id)],
        }
