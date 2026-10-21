# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_alterdata(self):
        """Campos entre aspas, separados por virgula, um lado por linha.

        Referencia: "","","1","01/08/2026","29,90","","historico","122333"
        """
        out = self._new_buffer()
        for move in self.move_ids:
            for line in self._get_export_lines(move):
                conta = self._resolve_account(line.account_id)[0]
                debito = bool(line.debit)
                campos = [
                    "",
                    conta if debito else "",
                    "" if debito else conta,
                    fh.format_date(move.date),
                    fh.format_amount(line.debit or line.credit),
                    "",
                    fh.clean_text(line.name or move.ref, 200, sep=","),
                    fh.clean_text(move.ref, 30, sep=","),
                ]
                out.write(fh.join_delimited(campos, ",", wrap='"'))
                out.write("\n")
        return [(self._file_name(), self._encode(out.getvalue()))]

    # ------------------------------------------------------------------
    # SCI: CSV por virgula, valor com ponto, data AAAAMMDD, zero no lado vazio
    # ------------------------------------------------------------------
