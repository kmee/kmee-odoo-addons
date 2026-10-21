# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

# Graus de risco do Quadro I da NR-4, atribuídos pelo CNAE da atividade.
GRAU_RISCO_NR4 = [
    ("1", "1"),
    ("2", "2"),
    ("3", "3"),
    ("4", "4"),
]


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_br_sst_grau_risco = fields.Selection(
        GRAU_RISCO_NR4,
        string="Grau de Risco (NR-4)",
        help="Grau de risco da organização, de 1 a 4, conforme o Quadro I da "
        "NR-4 para o CNAE da atividade. A NR-7 usa esse grau, por exemplo, "
        "para o prazo de dispensa do exame demissional (item 7.5.11). Vazio "
        "é tratado como o grau mais restritivo pelos módulos que o usam.",
    )
