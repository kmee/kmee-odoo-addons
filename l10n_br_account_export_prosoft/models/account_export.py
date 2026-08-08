# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_prosoft(self):
        """Prosoft: registros LC1 (cabecalho do lote) e LC2 (partidas)."""
        out = self._new_buffer()
        seq = 0
        for move in self.move_ids:
            seq += 1
            cabecalho = (
                "LC1"
                + fh.zero_pad(seq, 5)
                + fh.pad("", 3)
                + fh.format_date(move.date, "%d%m%Y")
                + fh.pad(fh.clean_text(move.ref, 10), 10)
                + fh.pad("", 5)
                + fh.pad("Omie", 30)
                + fh.pad("", 250)
            )
            out.write(fh.pad(cabecalho, 342) + "\n")
            for line in self._get_export_lines(move):
                detalhe = (
                    "LC2"
                    + fh.zero_pad(seq, 5)
                    + fh.zero_pad(1, 3)
                    + ("D" if line.debit else "C")
                    + fh.pad(self._resolve_account(line.account_id)[0], 20)
                    + fh.pad(
                        fh.format_amount(line.debit or line.credit, decimal_sep="."),
                        20,
                        align=fh.ALIGN_RIGHT,
                    )
                    + fh.pad(fh.clean_text(line.name or move.ref, 100), 100)
                )
                out.write(fh.pad(detalhe, 448) + "\n")
        return [(self._file_name(sufixo="ctblctos"), self._encode(out.getvalue()))]
