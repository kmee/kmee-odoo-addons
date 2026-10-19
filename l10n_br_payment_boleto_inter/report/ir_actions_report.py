# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.pdf import merge_pdf

BOLETO_REPORTS = {
    "l10n_br_payment_boleto_inter.action_report_account_move_boleto": "account.move",
    "l10n_br_payment_boleto_inter.action_report_sale_order_boleto": "sale.order",
}


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """Devolve o PDF do boleto emitido pelo banco.

        O boleto não é desenhado pelo Odoo: o PDF vem do Banco Inter e fica
        guardado na transação. Como um documento pode ter uma parcela por
        vencimento, os boletos são juntados num arquivo só.
        """
        model = BOLETO_REPORTS.get(report_ref)
        if not model:
            return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

        records = self.env[model].browse(res_ids)
        return self._render_boleto_inter(records)

    def _render_qweb_html(self, report_ref, res_ids=None, data=None):
        """O boleto só existe em PDF."""
        if report_ref in BOLETO_REPORTS:
            raise UserError(_("O boleto só pode ser impresso em PDF."))
        return super()._render_qweb_html(report_ref, res_ids=res_ids, data=data)

    def _render_boleto_inter(self, records):
        """Junta os boletos das transações dos registros.

        :param records: As faturas ou os pedidos a imprimir.
        :return: O PDF e o seu tipo.
        :rtype: tuple
        :raise UserError: Se nenhum boleto tiver sido emitido.
        """
        pdf_files = []
        for record in records:
            for transaction in record._get_boleto_inter_transactions():
                pdf_files.append(base64.b64decode(transaction.boleto_pdf))

        if not pdf_files:
            raise UserError(
                _("Nenhum boleto do Banco Inter foi emitido para este documento.")
            )
        if len(pdf_files) == 1:
            return pdf_files[0], "pdf"
        return merge_pdf(pdf_files), "pdf"
