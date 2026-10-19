# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_conttroller(self):
        """Referencia: 202608;1;1;000;000000;01/08/2026;hist;;29,90;"""
        out = self._new_buffer()
        periodo = self.date_start.strftime("%Y%m")
        seq = 0
        for move in self.move_ids:
            for line in self._get_export_lines(move):
                seq += 1
                valor = fh.format_amount(line.debit or line.credit)
                campos = [
                    periodo,
                    seq,
                    self._resolve_account(line.account_id)[0],
                    "000",
                    fh.zero_pad(0, 6),
                    fh.format_date(move.date),
                    fh.clean_text(line.name or move.ref, 200, sep=";"),
                    valor if line.debit else "",
                    "" if line.debit else valor,
                    "",
                ]
                out.write(fh.join_delimited(campos, ";"))
                out.write("\n")
        return [(self._file_name(), self._encode(out.getvalue()))]

    # ------------------------------------------------------------------
    # helpers compartilhados pelos layouts
    # ------------------------------------------------------------------
