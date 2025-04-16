from odoo import fields, models


class CrmStage(models.Model):
    _inherit = "crm.stage"

    role_responsible = fields.Selection(
        [("bdr", "BDR"), ("sdr", "SDR"), ("closer", "Closer"), ("default", "Default")],
        string="Stage Responsible",
        default="default",
    )
