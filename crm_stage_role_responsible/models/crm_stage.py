from odoo import fields, models


class CrmStage(models.Model):
    _inherit = "crm.stage"

    role_responsible = fields.Selection(
        [
            ("bdr", "BDR"),
            ("sdr", "SDR"),
            ("hunter", "Hunter"),
            ("closer", "Closer"),
            ("farmer", "Farmer"),
            ("default", "Default"),
        ],
        string="Stage Responsible",
        default="default",
    )
