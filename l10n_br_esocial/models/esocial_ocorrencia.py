# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESocialOcorrencia(models.Model):
    _name = "l10n_br.esocial.ocorrencia"
    _description = "eSocial - Ocorrência de Retorno"
    _order = "evento_id, tipo, codigo"

    evento_id = fields.Many2one(
        "l10n_br.esocial.evento",
        string="Evento",
        required=True,
        ondelete="cascade",
    )
    codigo = fields.Char(
        string="Código",
        size=10,
    )
    descricao = fields.Text(
        string="Descrição",
    )
    tipo = fields.Selection(
        [
            ("1", "Erro"),
            ("2", "Alerta"),
        ],
    )
    localizacao = fields.Char(
        string="Localização",
        help="Localização do erro no XML (XPath).",
    )
