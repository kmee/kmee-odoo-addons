# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    l10n_br_apuracao_dia_id = fields.Many2one(
        comodel_name="l10n_br.hr.apuracao.dia",
        string="Apuração do dia",
        ondelete="cascade",
        index=True,
        help="Apuração que gerou esta sessão. Sessões geradas pela apuração "
        "são refeitas a cada reprocessamento.",
    )
