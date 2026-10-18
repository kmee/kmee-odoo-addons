# (c) 2024 Kmee - Felipe Zago <felipe.zago@kmee.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    nationality_id = fields.Many2one(
        string="Nationality",
        store=True,
        related="address_home_id.country_id",
        readonly=False,
        groups="hr.group_hr_user",
    )

    rg_file = fields.Binary(string="RG File")

    cnh_file = fields.Binary(string="CNH File")

    voter_title_file = fields.Binary()

    reservist_file = fields.Binary()

    address_proof_file = fields.Binary()

    study_proof_file = fields.Binary()

    pis_file = fields.Binary()
