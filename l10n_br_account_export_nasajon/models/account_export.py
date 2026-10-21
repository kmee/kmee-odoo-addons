# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_nasajon(self):
        """Nasajon: posicional, conta, historico e valor."""
        out = self._new_buffer()
        for move in self.move_ids:
            for line in self._get_export_lines(move):
                linha = (
                    move.date.strftime("%d%m")
                    + fh.zero_pad(0, 1)
                    + fh.pad(self._resolve_account(line.account_id)[0], 20)
                    + fh.pad("", 5)
                    + fh.pad(fh.clean_text(line.name or move.ref, 50), 50)
                    + fh.pad(
                        fh.format_amount(line.debit or line.credit),
                        16,
                        align=fh.ALIGN_RIGHT,
                    )
                    + " "
                    + fh.pad(fh.clean_text(move.ref, 20), 20)
                )
                out.write(linha + "\n")
        return [(self._file_name(), self._encode(out.getvalue()))]
