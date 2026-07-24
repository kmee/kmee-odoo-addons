from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_br_esocial_matricula = fields.Char(
        string="Matrícula eSocial",
        size=30,
        help="Matrícula atribuída ao trabalhador pela empresa.",
    )
    l10n_br_esocial_categoria_id = fields.Many2one(
        "l10n_br.esocial.categoria.trabalhador",
        string="Categoria Trabalhador eSocial",
        help="Categoria do trabalhador conforme Tabela 1 do eSocial.",
    )
