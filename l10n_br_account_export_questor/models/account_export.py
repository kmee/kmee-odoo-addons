# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_questor(self):
        """Questor, 445 posicoes.

        Referencia: espaco + campos numericos zero-padded + data dupla
        (AAAAMMDD e dd/mm/aaaa) + documento + contas + valor + historico.
        """
        out = self._new_buffer()
        seq = 0
        for move in self.move_ids:
            for conta_d, conta_c, valor, hist, data in self._pair_entries(move):
                seq += 1
                linha = (
                    " "
                    + fh.zero_pad(1, 5)
                    + fh.zero_pad(0, 20)
                    + fh.zero_pad(seq, 8)
                    + fh.zero_pad(1, 2)
                    + fh.format_date(data, "%Y%m%d")
                    + fh.format_date(data)
                    + "LN"
                    + fh.pad(fh.clean_text(move.ref, 12), 12)
                    + fh.zero_pad(conta_d or 0, 12)
                    + fh.zero_pad(conta_c or 0, 12)
                    + fh.amount_cents(valor, 12)
                    + fh.pad(fh.clean_text(hist, 200), 200)
                )
                out.write(fh.pad(linha, 445) + "\n")
        return [(self._file_name(), self._encode(out.getvalue()))]
