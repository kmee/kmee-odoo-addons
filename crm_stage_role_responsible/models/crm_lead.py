from odoo import _, api, exceptions, fields, models

ROLES = ["sdr_bdr", "hunter", "closer", "farmer"]


class CrmLead(models.Model):
    _inherit = "crm.lead"

    sdr_bdr_id = fields.Many2one(
        "res.users",
        string="SDR/BDR",
        domain="['&', ('share', '=', False), ('company_ids', 'in', user_company_ids)]",
    )
    hunter_id = fields.Many2one(
        "res.users",
        string="Hunter",
        domain="['&', ('share', '=', False), ('company_ids', 'in', user_company_ids)]",
    )
    closer_id = fields.Many2one(
        "res.users",
        string="Closer",
        domain="['&', ('share', '=', False), ('company_ids', 'in', user_company_ids)]",
    )
    farmer_id = fields.Many2one(
        "res.users",
        string="Farmer",
        domain="['&', ('share', '=', False), ('company_ids', 'in', user_company_ids)]",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsável",
        default=lambda self: self.env.user,
        domain="['&', ('share', '=', False), ('company_ids', 'in', user_company_ids)]",
        check_company=True,
        index=True,
        tracking=True,
    )
    hide_sdr_bdr = fields.Boolean(string="Hide SDR/BDR", related="team_id.hide_sdr_bdr", store=True)
    hide_hunter = fields.Boolean(
        string="Hide Hunter", related="team_id.hide_hunter", store=True
    )
    hide_closer = fields.Boolean(
        string="Hide Closer", related="team_id.hide_closer", store=True
    )
    hide_farmer = fields.Boolean(
        string="Hide Farmer", related="team_id.hide_farmer", store=True
    )

    def _assign_user_from_role(self):
        for lead in self:
            role = lead.stage_id.role_responsible
            for r in ROLES:
                if role == r:
                    field_name = f"{role}_id"
                    user = getattr(lead, field_name, False)
                    if user:
                        lead.user_id = user
                    else:
                        role_display = role.replace("_", "/").upper()
                        raise exceptions.UserError(
                            _(f"Current stage requires a {role_display} assignment.")
                        )

    @api.model
    def create(self, vals):
        lead = super().create(vals)
        lead._assign_user_from_role()
        return lead

    def write(self, vals):
        res = super().write(vals)
        if "stage_id" in vals or "type" in vals:
            self._assign_user_from_role()
        return res

    def _prepare_opportunity_quotation_context(self):
        quotation_context = super()._prepare_opportunity_quotation_context()
        quotation_context.update(
            {
                "default_sdr_bdr_id": self.sdr_bdr_id.id if self.sdr_bdr_id else False,
                "default_hunter_id": self.hunter_id.id if self.hunter_id else False,
                "default_closer_id": self.closer_id.id if self.closer_id else False,
                "default_farmer_id": self.farmer_id.id if self.farmer_id else False,
            }
        )
        return quotation_context
