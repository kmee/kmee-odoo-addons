from odoo import fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    l10n_br_esocial_motivo_deslig_id = fields.Many2one(
        "l10n_br.esocial.motivo.desligamento",
        string="Motivo Desligamento eSocial",
        help="Motivo do desligamento conforme Tabela 19 do eSocial.",
    )
