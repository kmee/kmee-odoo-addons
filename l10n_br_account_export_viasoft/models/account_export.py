# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_viasoft(self):
        """Viasoft: sequencial, data, contas e valor em largura fixa."""
        out = self._new_buffer()
        seq = 0
        for move in self.move_ids:
            for conta_d, conta_c, valor, hist, data in self._pair_entries(move):
                seq += 1
                linha = (
                    fh.zero_pad(1, 3)
                    + fh.zero_pad(seq, 3)
                    + fh.format_date(data, "%d%m%Y")
                    + fh.pad(conta_d, 15)
                    + fh.pad(conta_c, 22)
                    + fh.pad(fh.format_amount(valor), 10, align=fh.ALIGN_RIGHT)
                    + fh.pad("", 3)
                    + fh.pad(fh.clean_text(hist, 100), 100)
                )
                out.write(linha + "\n")
        return [(self._file_name(), self._encode(out.getvalue()))]
