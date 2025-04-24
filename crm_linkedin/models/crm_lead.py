from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    linkedin_url = fields.Char(
        string="LinkedIn Profile",
        help="Contact's LinkedIn profile URL",
        compute="_compute_linkedin_url",
        inverse="_inverse_linkedin_url",
        store=True,
        readonly=False,
    )

    @api.depends("partner_id.linkedin_url")
    def _compute_linkedin_url(self):
        for lead in self:
            if lead.partner_id and lead.partner_id.linkedin_url:
                lead.linkedin_url = lead.partner_id.linkedin_url

    def _inverse_linkedin_url(self):
        for lead in self:
            if lead.partner_id:
                lead.partner_id.linkedin_url = lead.linkedin_url

    def _prepare_customer_values(self, partner_name, is_company=False, parent_id=False):
        """Adiciona o campo linkedin_url aos valores do cliente"""
        values = super()._prepare_customer_values(
            partner_name, is_company=is_company, parent_id=parent_id
        )
        if self.linkedin_url:
            values["linkedin_url"] = self.linkedin_url
        return values
