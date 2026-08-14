# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class L10nBrHrMarcacao(models.Model):
    _inherit = "l10n_br.hr.marcacao"

    afd_import_id = fields.Many2one(
        comodel_name="l10n_br.hr.afd.import",
        string="Importação de AFD",
        readonly=True,
        ondelete="set null",
        index=True,
        help="Lote em que esta marcação entrou no sistema. Preserva a "
        "rastreabilidade até o arquivo original entregue pelo relógio.",
    )
