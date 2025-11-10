from odoo import fields, models


class CrmStage(models.Model):
    _inherit = "crm.stage"

    role_responsible = fields.Selection(
        [
            ("sdr_bdr", "SDR/BDR"),
            ("hunter", "Hunter"),
            ("closer", "Closer"),
            ("farmer", "Farmer"),
            ("default", "Default"),
        ],
        string="Stage Responsible",
        default="default",
    )
