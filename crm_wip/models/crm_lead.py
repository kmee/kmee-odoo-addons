from odoo import fields, models


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = ["base.wip.abstract", "crm.lead"]

    state = fields.Selection(
        string="Stage State",
        related="stage_id.state",
        store=True,
    )
