# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CreditRestriction(models.Model):
    _name = "credit.restriction"
    _description = "Restricao de Credito"
    _order = "date desc, id desc"

    analysis_id = fields.Many2one(
        comodel_name="credit.analysis",
        string="Consulta de Credito",
        required=True,
        ondelete="cascade",
    )
    type = fields.Selection(
        selection=[
            ("negativacao", "Negativacao"),
            ("protesto", "Protesto"),
            ("acao_judicial", "Acao Judicial"),
            ("cheque_sem_fundo", "Cheque sem Fundo"),
            ("cheque_sustado", "Cheque Sustado"),
            ("cheque_devolvido", "Cheque Devolvido"),
            ("falencia", "Falencia"),
            ("recuperacao_judicial", "Recuperacao Judicial"),
        ],
        string="Tipo",
        required=True,
    )
    date = fields.Date(
        string="Data",
    )
    value = fields.Monetary(
        string="Valor",
        currency_field="currency_id",
    )
    creditor = fields.Char(
        string="Credor/Autor",
    )
    description = fields.Text(
        string="Descricao",
    )
    details = fields.Text(
        string="Detalhes",
        help="Numero do processo, cartorio, etc.",
    )
    state = fields.Selection(
        selection=[
            ("active", "Ativa"),
            ("resolved", "Resolvida"),
        ],
        string="Situacao",
        default="active",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moeda",
        default=lambda self: self.env.company.currency_id,
    )

    # Related fields
    company_id = fields.Many2one(
        string="Empresa",
        related="analysis_id.company_id",
        store=True,
    )

    def name_get(self):
        result = []
        type_labels = dict(
            self._fields["type"].selection
        )
        for record in self:
            type_name = type_labels.get(record.type, record.type)
            if record.value:
                name = f"{type_name} - R$ {record.value:,.2f}"
            else:
                name = type_name
            result.append((record.id, name))
        return result
