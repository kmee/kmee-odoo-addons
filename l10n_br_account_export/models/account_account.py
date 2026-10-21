# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    l10n_br_export_code = fields.Char(
        string="Codigo no escritorio",
        size=20,
        copy=False,
        index=True,
        help="Codigo reduzido desta conta no plano de contas do escritorio de "
        "contabilidade. E o codigo que vai no arquivo; sem ele, as partidas "
        "desta conta sao recusadas com critica.",
    )
