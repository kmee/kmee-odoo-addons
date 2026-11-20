# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io
import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:  # pragma: no cover
    _logger.debug("xlsxwriter not available")


class PurchaseRfqRound(models.Model):
    _inherit = "purchase.rfq.round"

    # ------------------------------------------------------------------
    # Planilha de resposta
    # ------------------------------------------------------------------

    def _get_sheet_columns(self):
        """Colunas da planilha de resposta.

        Cada coluna: chave, título, largura, se o fornecedor preenche e uma
        função que devolve o valor inicial a partir da linha da cotação.
        Módulos podem acrescentar colunas (por exemplo, condição de pagamento).
        """
        return [
            {
                "key": "line_id",
                "label": "ID",
                "width": 8,
                "input": False,
                "value": lambda pol: pol.id,
            },
            {
                "key": "default_code",
                "label": _("Code"),
                "width": 14,
                "input": False,
                "value": lambda pol: pol.product_id.default_code or "",
            },
            {
                "key": "product",
                "label": _("Product"),
                "width": 40,
                "input": False,
                "value": lambda pol: pol.product_id.display_name,
            },
            {
                "key": "uom",
                "label": _("UoM"),
                "width": 8,
                "input": False,
                "value": lambda pol: pol.product_uom.name,
            },
            {
                "key": "quantity",
                "label": _("Quantity"),
                "width": 10,
                "input": False,
                "value": lambda pol: pol.product_qty,
            },
            {
                "key": "price_unit",
                "label": _("Unit Price"),
                "width": 12,
                "input": True,
                "value": lambda pol: pol.price_unit or None,
            },
            {
                "key": "delay",
                "label": _("Delivery Lead Time (days)"),
                "width": 12,
                "input": True,
                "value": lambda pol: None,
            },
            {
                "key": "note",
                "label": _("Notes"),
                "width": 30,
                "input": True,
                "value": lambda pol: None,
            },
        ]

    def _generate_response_sheet(self, order):
        """Gera a planilha padrão de resposta de uma cotação da rodada."""
        self.ensure_one()
        output = io.BytesIO()
        book = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = book.add_worksheet(_("Quotation"))
        bold = book.add_format({"bold": True})
        head = book.add_format({"bold": True, "bg_color": "#D9E1F2", "border": 1})
        locked = book.add_format({"locked": True, "bg_color": "#F2F2F2"})
        unlocked = book.add_format({"locked": False, "bg_color": "#FFF2CC"})
        sheet.write(0, 0, _("Quotation round"), bold)
        sheet.write(0, 1, self.name)
        sheet.write(1, 0, _("Quotation"), bold)
        sheet.write(1, 1, order.name)
        sheet.write(2, 0, _("Vendor"), bold)
        sheet.write(2, 1, order.partner_id.display_name)
        sheet.write(3, 0, _("Answer deadline"), bold)
        sheet.write(3, 1, fields.Date.to_string(self.date_deadline) or "")
        columns = self._get_sheet_columns()
        header_row = 5
        for col, column in enumerate(columns):
            sheet.write(header_row, col, column["label"], head)
            sheet.set_column(col, col, column["width"])
        for row, pol in enumerate(order.order_line.filtered("product_id"), 1):
            for col, column in enumerate(columns):
                value = column["value"](pol)
                fmt = unlocked if column["input"] else locked
                if value is None:
                    sheet.write_blank(header_row + row, col, None, fmt)
                else:
                    sheet.write(header_row + row, col, value, fmt)
        sheet.protect("", {"format_columns": True})
        book.close()
        return output.getvalue()

    def _attach_response_sheet(self, order):
        self.ensure_one()
        content = self._generate_response_sheet(order)
        return self.env["ir.attachment"].create(
            {
                "name": f"{order.name.replace('/', '-')}.xlsx",
                "datas": base64.b64encode(content),
                "res_model": "purchase.order",
                "res_id": order.id,
                "mimetype": (
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
            }
        )

    def _get_rfq_mail_attachments(self, order):
        attachments = super()._get_rfq_mail_attachments(order)
        return attachments | self._attach_response_sheet(order)

    def action_import_responses(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Import Responses"),
            "res_model": "purchase.rfq.round.import",
            "view_mode": "form",
            "target": "new",
            "context": {"default_round_id": self.id},
        }
