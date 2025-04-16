from odoo import _, api, exceptions, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    bdr_id = fields.Many2one("res.users", string="BDR")
    sdr_id = fields.Many2one("res.users", string="SDR")
    closer_id = fields.Many2one("res.users", string="Closer")

    def _assign_user_from_role(self):
        for lead in self:
            role = lead.stage_id.role_responsible
            if role == "bdr":
                if lead.bdr_id:
                    lead.user_id = lead.bdr_id
                else:
                    raise exceptions.UserError(
                        _("Current stage requires a BDR assignment.")
                    )
            elif role == "sdr":
                if lead.sdr_id:
                    lead.user_id = lead.sdr_id
                else:
                    raise exceptions.UserError(
                        _("Current stage requires a SDR assignment.")
                    )
            elif role == "closer":
                if lead.closer_id:
                    lead.user_id = lead.closer_id
                else:
                    raise exceptions.UserError(
                        _("Current stage requires a Closer assignment.")
                    )

    @api.model
    def create(self, vals):
        lead = super().create(vals)
        lead._assign_user_from_role()
        return lead

    def write(self, vals):
        res = super().write(vals)
        if "stage_id" in vals:
            self._assign_user_from_role()
        return res

    def _prepare_opportunity_quotation_context(self):
        quotation_context = super()._prepare_opportunity_quotation_context()
        quotation_context.update(
            {
                "default_bdr_id": self.bdr_id.id if self.bdr_id else False,
                "default_sdr_id": self.sdr_id.id if self.sdr_id else False,
                "default_closer_id": self.closer_id.id if self.closer_id else False,
            }
        )
        return quotation_context
