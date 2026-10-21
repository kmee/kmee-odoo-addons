# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_exactus(self):
        """Exactus, 180 posicoes, campos numericos zero-padded."""
        out = self._new_buffer()
        seq = 0
        for move in self.move_ids:
            for conta_d, conta_c, valor, hist, data in self._pair_entries(move):
                seq += 1
                linha = (
                    fh.zero_pad(seq, 7)
                    + fh.zero_pad(conta_d or 0, 15)
                    + fh.zero_pad(conta_c or 0, 15)
                    + fh.pad(fh.clean_text(move.ref, 10), 10)
                    + fh.pad(fh.clean_text(hist, 100), 100)
                    + fh.amount_cents(valor, 15)
                    + fh.format_date(data, "%d%m%y")
                )
                out.write(fh.pad(linha, 180) + "\n")
        return [(self._file_name(), self._encode(out.getvalue()))]
