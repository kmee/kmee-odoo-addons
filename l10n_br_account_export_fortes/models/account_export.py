# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_fortes(self):
        """Fortes AG (.CT): registro 0010 de abertura e 1004 por partida."""
        out = self._new_buffer()
        cabecalho = (
            "0010"
            + fh.pad("AC", 10)
            + fh.pad("OMIE", 10)
            + fh.pad(self.config_id.company_code or "1", 4)
            + fh.format_date(self.date_start, "%Y%m%d")
            + fh.format_date(self.date_end, "%Y%m%d")
            + fh.pad("Integracao contabil", 40)
        )
        out.write(fh.pad(cabecalho, 84) + "\n")
        seq = 0
        for move in self.move_ids:
            for line in self._get_export_lines(move):
                seq += 1
                linha = (
                    "1004"
                    + fh.format_date(move.date, "%Y%m%d")
                    + fh.zero_pad(seq, 10)
                    + move.date.strftime("%Y%m")
                    + fh.pad("", 4)
                    + fh.pad(line.account_id.l10n_br_export_code or "", 20)
                    + fh.pad(
                        fh.format_amount(
                            line.debit or line.credit, decimal_sep=".", decimals=6
                        ),
                        20,
                        align=fh.ALIGN_RIGHT,
                    )
                    + fh.pad(fh.clean_text(line.name or move.ref, 40), 40)
                )
                out.write(fh.pad(linha, 116) + "\n")
        return [(self._file_name(extensao="CT"), self._encode(out.getvalue()))]
