from odoo import fields, models


class Contract(models.Model):
    _inherit = "contract.contract"

    sign_request_id = fields.Many2one("sign.request", string="Sign Request")
    sign_status = fields.Selection(
        related="sign_request_id.state", string="Sign Status", store=True
    )
