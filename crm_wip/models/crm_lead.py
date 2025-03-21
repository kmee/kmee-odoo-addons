from odoo import fields, models


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = ["base.wip.abstract", "crm.lead"]

    state = fields.Selection(
        related="stage_id.state",
        store=True,
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | {"state"}
