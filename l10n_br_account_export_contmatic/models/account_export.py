# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_contmatic(self):
        """Contmatic Phoenix, 332 posicoes.

        Referencia: 680000101/085      1                  29.900    historico
        Prefixo 68, sequencial, data dd/mm, contas e valor com ponto.
        """
        out = self._new_buffer()
        seq = 0
        for move in self.move_ids:
            for conta_d, conta_c, valor, hist, data in self._pair_entries(move):
                seq += 1
                linha = (
                    "68"
                    + fh.zero_pad(seq, 5)
                    + fh.format_date(data, "%d/%m")
                    + fh.pad(conta_d, 7)
                    + fh.pad(conta_c, 19)
                    + fh.pad(
                        fh.format_amount(valor, decimal_sep=".", decimals=3),
                        12,
                        align=fh.ALIGN_RIGHT,
                    )
                    + fh.pad("", 4)
                    + fh.pad(fh.clean_text(hist, 200), 200)
                )
                out.write(fh.pad(linha, 332) + "\n")
        return [(self._file_name(), self._encode(out.getvalue()))]
