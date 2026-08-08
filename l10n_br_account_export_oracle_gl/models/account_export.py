# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import io

from odoo import _, models
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:  # pragma: no cover
    xlsxwriter = None


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _sheet_rows(self, colunas):
        """Uma linha de planilha por partida, na ordem das colunas pedidas."""
        self.ensure_one()
        linhas = []
        for move in self.move_ids:
            for line in self._get_export_lines(move):
                valores = {
                    "data": move.date and move.date.strftime("%d/%m/%Y") or "",
                    "lancamento": move.name or "",
                    "conta": line.account_id.l10n_br_export_code or "",
                    "conta_odoo": line.account_id.code or "",
                    "debito": line.debit,
                    "credito": line.credit,
                    "historico": line.name or move.ref or "",
                    "documento": move.ref or "",
                    "parceiro": line.partner_id.display_name or "",
                    "diario": move.journal_id.code or "",
                    "moeda": self.company_id.currency_id.name,
                }
                linhas.append([valores.get(c, "") for c in colunas])
        return linhas

    def _build_xlsx(self, titulos, colunas, aba="Lancamentos"):
        if xlsxwriter is None:
            raise UserError(
                _(
                    "A biblioteca xlsxwriter e necessaria para os layouts em "
                    "planilha. Instale-a no servidor."
                )
            )
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
        sheet = workbook.add_worksheet(aba)
        negrito = workbook.add_format({"bold": True})
        moeda = workbook.add_format({"num_format": "#,##0.00"})
        for col, titulo in enumerate(titulos):
            sheet.write(0, col, titulo, negrito)
        for idx, linha in enumerate(self._sheet_rows(colunas), start=1):
            for col, valor in enumerate(linha):
                if isinstance(valor, float):
                    sheet.write_number(idx, col, valor, moeda)
                else:
                    sheet.write(idx, col, valor)
        workbook.close()
        buffer.seek(0)
        return buffer.read()

    def _generate_oracle_gl(self):
        """Oracle GL Interface: colunas no vocabulario do GL."""
        titulos = [
            "ACCOUNTING_DATE",
            "SEGMENT",
            "ENTERED_DR",
            "ENTERED_CR",
            "REFERENCE",
            "CURRENCY_CODE",
        ]
        colunas = ["data", "conta", "debito", "credito", "historico", "moeda"]
        return [
            (
                self._file_name(sufixo="GL_INTERFACE", extensao="xlsx"),
                self._build_xlsx(titulos, colunas, aba="GL_INTERFACE"),
            )
        ]
