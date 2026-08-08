# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_protheus(self):
        """TOTVS Protheus, 139 posicoes.

        Referencia: 001001   5<...>1<...>00000000000002990   historico
        Valor em centavos, zero a esquerda.
        """
        out = self._new_buffer()
        seq = 0
        for move in self.move_ids:
            for conta_d, conta_c, valor, hist, _data in self._pair_entries(move):
                seq += 1
                linha = (
                    fh.zero_pad(seq, 6)
                    + fh.pad("", 3)
                    + fh.pad(conta_d, 40)
                    + fh.pad(conta_c, 30)
                    + fh.amount_cents(valor, 17)
                    + fh.pad("", 3)
                    + fh.pad(fh.clean_text(hist, 40), 40)
                )
                out.write(fh.pad(linha, 139) + "\n")
        return [(self._file_name(), self._encode(out.getvalue()))]
