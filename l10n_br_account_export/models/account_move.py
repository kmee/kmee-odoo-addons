# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_br_account_export_id = fields.Many2one(
        "l10n_br.account.export",
        string="Exportacao contabil",
        check_company=True,
        copy=False,
        readonly=True,
        index=True,
        ondelete="set null",
        help="Lote em que este lancamento foi enviado ao escritorio. Enquanto "
        "preenchido, o lancamento nao entra em nenhuma outra exportacao.",
    )
