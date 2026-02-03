# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CreditPartnerParticipation(models.Model):
    _name = "credit.partner.participation"
    _description = "Participacao Societaria em Outras Empresas"
    _order = "participation desc"

    partner_id = fields.Many2one(
        comodel_name="credit.partner",
        string="Socio",
        required=True,
        ondelete="cascade",
    )
    cnpj = fields.Char(
        string="CNPJ",
    )
    razao_social = fields.Char(
        string="Razao Social",
    )
    participation = fields.Float(
        string="Participacao (%)",
        digits=(5, 2),
    )
    situation = fields.Selection(
        selection=[
            ("ativo", "Ativo"),
            ("baixado", "Baixado"),
        ],
        string="Situacao",
        default="ativo",
    )
    entry_date = fields.Date(
        string="Data de Entrada",
    )
    has_debts = fields.Boolean(
        string="Possui Debitos",
        default=False,
    )
    has_fraud = fields.Boolean(
        string="Possui Fraude",
        default=False,
    )
    negativacoes_value = fields.Monetary(
        string="Valor Negativacoes",
        currency_field="currency_id",
    )
    protestos_value = fields.Monetary(
        string="Valor Protestos",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moeda",
        default=lambda self: self.env.company.currency_id,
    )
