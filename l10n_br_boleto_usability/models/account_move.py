# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.l10n_br_fiscal.constants.fiscal import SITUACAO_EDOC_AUTORIZADA


class AccountMove(models.Model):

    _inherit = "account.move"

    def view_boleto_pdf(self):
        for record in self:
            for edoc in record.fiscal_document_ids:
                if edoc.state_edoc != SITUACAO_EDOC_AUTORIZADA:
                    raise UserError(
                        _("Emita o documento fiscal antes de imprimir o boleto.")
                    )
        return super().view_boleto_pdf()
