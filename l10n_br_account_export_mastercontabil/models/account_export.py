# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_mastercontabil(self):
        """Master Contabil, 121 posicoes.

        Referencia: 20260801122333  5<...>1<...>29.90   historico<...>0000
        """
        out = self._new_buffer()
        for move in self.move_ids:
            for conta_d, conta_c, valor, hist, data in self._pair_entries(move):
                linha = (
                    fh.format_date(data, "%Y%m%d")
                    + fh.pad(fh.clean_text(move.ref, 8), 8)
                    + fh.pad(conta_d, 17)
                    + fh.pad(conta_c, 25)
                    + fh.pad(
                        fh.format_amount(valor, decimal_sep="."),
                        8,
                        align=fh.ALIGN_RIGHT,
                    )
                    + fh.pad("", 3)
                    + fh.pad(fh.clean_text(hist, 48), 48)
                    + "0000"
                )
                out.write(fh.pad(linha, 121) + "\n")
        return [(self._file_name(), self._encode(out.getvalue()))]
