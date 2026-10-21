# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_ignis(self):
        """Referencia: 01/08/2026;5<20>;1<20>;valor<19 dir>;doc<10>;hist<66>"""
        out = self._new_buffer()
        for move in self.move_ids:
            for conta_d, conta_c, valor, hist, data in self._pair_entries(move):
                campos = [
                    fh.format_date(data),
                    fh.pad(conta_d, 20),
                    fh.pad(conta_c, 20),
                    fh.pad(fh.format_amount(valor), 19, align=fh.ALIGN_RIGHT),
                    fh.pad(fh.clean_text(move.ref, 10, sep=";"), 10),
                    fh.pad(fh.clean_text(hist, 66, sep=";"), 66),
                ]
                out.write(fh.join_delimited(campos, ";"))
                out.write("\n")
        return [(self._file_name(), self._encode(out.getvalue()))]

    # ------------------------------------------------------------------
    # Conttroller: ponto e virgula, debito e credito em colunas separadas
    # ------------------------------------------------------------------
