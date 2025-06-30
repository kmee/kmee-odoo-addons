# models/sign_request.py

from odoo import fields, models


class SignRequest(models.Model):
    _inherit = "sign.request"

    contract_id = fields.Many2one("contract.contract", string="Contract")
