# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountExportConfig(models.Model):
    """Perfil de exportacao: o layout do destino e o que varia por escritorio.

    O layout em si e codigo (a estrutura do arquivo e especificacao de
    terceiro); aqui ficam apenas os parametros que mudam de cliente para
    cliente, e que o usuario precisa poder ajustar sem programador.
    """

    _name = "l10n_br.account.export.config"
    _description = "Configuracao de Exportacao Contabil"

    name = fields.Char(required=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    layout = fields.Selection(
        selection=[],
        string="Layout do destino",
        required=True,
        help="Sistema contabil do escritorio. Cada layout e implementado por um "
        "adapter do modulo de layouts.",
    )
    encoding = fields.Selection(
        [
            ("cp1252", "Windows-1252 (ANSI)"),
            ("latin-1", "ISO-8859-1"),
            ("utf-8", "UTF-8"),
        ],
        default="cp1252",
        required=True,
        help="A maioria dos sistemas brasileiros importa em ANSI.",
    )
    mapping_plan_id = fields.Many2one(
        comodel_name="l10n_br.account.mapping.plan",
        string="Plano de contas do destino",
        help="Quando definido, os codigos de conta do arquivo saem do "
        "mapeamento deste plano (N contas do Odoo por conta do destino). Sem "
        "plano, vale o campo Codigo no escritorio de cada conta (1:1).",
    )
    company_code = fields.Char(
        string="Codigo da empresa no escritorio",
        size=20,
        help="Codigo desta empresa no sistema do escritorio, quando o layout "
        "exigir no registro de cabecalho.",
    )
    active = fields.Boolean(default=True)
