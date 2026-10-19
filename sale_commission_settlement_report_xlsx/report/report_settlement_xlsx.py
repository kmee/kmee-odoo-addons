# Copyright 2025 Luis Mileo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models


class ReportCommissionSettlementXlsx(models.AbstractModel):
    _name = "report.sale_commission.settlement_xls"
    _inherit = "report.report_xlsx.abstract"
    _description = "XLSX Report to show commission settlements"

    def _get_headers(self):
        return [
            _("Invoice Date"),
            _("Invoice"),
            _("Customer"),
            _("Invoice Line"),
            _("Amount Invoice"),
            _("Commission"),
            _("Amount Settled"),
        ]

    def _get_currency_format(self, workbook, formats, currency, bold=False):
        """One format per currency and weight, a workbook has a limit of formats."""
        key = (currency.id, bold)
        if key not in formats:
            formats[key] = workbook.add_format(
                {
                    "bold": bold,
                    "bg_color": "#FFFFCC" if bold else False,
                    # the symbol is quoted: it can have characters with a meaning
                    "num_format": '"%s"#,##0.00' % (currency.symbol or ""),
                }
            )
        return formats[key]

    def _generate_headers(self, sheet, row, bold, settlement):
        """Write the settlement header, uses 4 rows, and return the next row."""
        sheet.write(row, 0, _("Agent"), bold)
        sheet.write(row, 1, _("From"), bold)
        sheet.write(row, 2, _("To"), bold)

        sheet.write(row + 1, 0, settlement.agent_id.display_name, bold)
        sheet.write(row + 1, 1, settlement.date_from.isoformat(), bold)
        sheet.write(row + 1, 2, settlement.date_to.isoformat(), bold)

        for col, header in enumerate(self._get_headers()):
            sheet.write(row + 3, col, header, bold)
        return row + 4

    def _generate_lines(self, workbook, sheet, row, formats, settlement):
        """Write the settlement lines and return the next row and the rows data."""
        no_bold = workbook.add_format({"bold": False})
        currency_format = self._get_currency_format(
            workbook, formats, settlement.currency_id
        )
        rows_data = []
        for line in settlement.line_ids:
            invoice_line = line.invoice_line_id
            row_data = [
                line.date.isoformat() if line.date else "",
                invoice_line.move_id.name or "",
                invoice_line.move_id.partner_id.display_name or "",
                invoice_line.name or "",
                invoice_line.price_total,
                line.commission_id.display_name or "",
                line.settled_amount,
            ]
            rows_data.append(row_data)
            for col, value in enumerate(row_data):
                # Amount Invoice and Amount Settled are monetary
                cell_format = currency_format if col in (4, 6) else no_bold
                sheet.write(row, col, value, cell_format)
            row += 1
        return row, rows_data

    def _generate_footer(self, workbook, sheet, row, bold, settlement, formats):
        """Write the total of the settlement and return the next row."""
        total_format = self._get_currency_format(
            workbook, formats, settlement.currency_id, bold=True
        )
        sheet.write(row, 5, _("Total Commissions"), bold)
        sheet.write(row, 6, settlement.total, total_format)
        return row + 1

    def _adjust_column_width(self, sheet, data):
        """Automatically adjust column widths based on content."""
        for col, header in enumerate(self._get_headers()):
            max_length = len(header)
            for row in data:
                max_length = max(max_length, len(str(row[col])))
            sheet.set_column(col, col, max_length + 2)

    def generate_xlsx_report(self, workbook, data, settlements):
        sheet = workbook.add_worksheet("Commission Settlements")
        bold = workbook.add_format({"bold": True, "bg_color": "#FFFFCC"})
        formats = {}
        row = 0
        data_rows = []
        for settlement in settlements:
            row = self._generate_headers(sheet, row, bold, settlement)
            row, rows_data = self._generate_lines(
                workbook, sheet, row, formats, settlement
            )
            data_rows += rows_data
            row = self._generate_footer(workbook, sheet, row, bold, settlement, formats)
            row += 2  # blank rows between settlements
        self._adjust_column_width(sheet, data_rows)
