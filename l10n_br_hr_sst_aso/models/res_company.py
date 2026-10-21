# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_br_sst_aso_politica = fields.Selection(
        [
            ("ignora", "Não verificar"),
            ("alerta", "Alertar no chatter"),
            ("bloqueia", "Bloquear a operação"),
        ],
        string="Política de ASO",
        default="alerta",
        required=True,
        help="O que fazer quando o contrato é aberto sem o ASO admissional "
        "concluído (NR-7, item 7.5.8, I). O demissional nunca bloqueia: tem "
        "prazo de 10 dias depois do término e é cobrado por atividade, salvo "
        "a dispensa do item 7.5.11. 'Não verificar' desliga as duas coisas.",
    )
    l10n_br_sst_aso_alerta_dias = fields.Integer(
        string="Antecedência do Periódico (dias)",
        default=30,
        help="Antecedência com que o exame periódico é agendado antes do "
        "vencimento do ASO anterior.",
    )
