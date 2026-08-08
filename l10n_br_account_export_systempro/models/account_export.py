# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_systempro(self):
        """Systempro, 544 posicoes: AAAAMM + dia + conta + historico."""
        out = self._new_buffer()
        for move in self.move_ids:
            for line in self._get_export_lines(move):
                linha = (
                    move.date.strftime("%Y%m")
                    + move.date.strftime("%d")
                    + fh.zero_pad(0, 4)
                    + fh.pad(
                        line.account_id.l10n_br_export_code or "",
                        5,
                        align=fh.ALIGN_RIGHT,
                    )
                    + fh.pad(fh.clean_text(line.name or move.ref, 200), 200)
                )
                out.write(fh.pad(linha, 544) + "\n")
        return [(self._file_name(), self._encode(out.getvalue()))]
