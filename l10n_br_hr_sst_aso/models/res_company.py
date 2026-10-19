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
        help="O que fazer quando o contrato é aberto ou encerrado sem o ASO "
        "correspondente concluído (NR-7).",
    )
    l10n_br_sst_aso_alerta_dias = fields.Integer(
        string="Antecedência do Periódico (dias)",
        default=30,
        help="Antecedência com que o exame periódico é agendado antes do "
        "vencimento do ASO anterior.",
    )
