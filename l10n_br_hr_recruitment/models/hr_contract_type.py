# (c) 2024 Kmee - Felipe Zago <felipe.zago@kmee.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class HrApplicant(models.Model):
    _inherit = "hr.contract.type"

    regime = fields.Selection(
        selection=[
            ("CLT", "CLT"),
            ("PJ", "PJ"),
            ("other", "Outros"),
        ],
        default="CLT",
    )
