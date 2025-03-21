from odoo import api, fields, models


class CrmStage(models.Model):
    _inherit = "crm.stage"

    @api.model
    def _get_lead_states(self):
        return [
            ("draft", "New"),
            ("open", "In Progress"),
            ("pending", "Pending"),
            ("done", "Won"),
            ("cancelled", "Lost"),
        ]

    state = fields.Selection(
        selection="_get_lead_states",
    )
