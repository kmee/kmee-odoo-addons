# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_sci(self):
        """Referencia: 000001,20260801,0,00000001,29.90,00000000,hist,DOC,cnpj,,"""
        out = self._new_buffer()
        seq = 0
        for move in self.move_ids:
            for line in self._get_export_lines(move):
                seq += 1
                conta = fh.zero_pad(self._resolve_account(line.account_id)[0] or "0", 8)
                debito = bool(line.debit)
                campos = [
                    fh.zero_pad(seq, 6),
                    fh.format_date(move.date, "%Y%m%d"),
                    conta if debito else "0",
                    "0" if debito else conta,
                    fh.format_amount(line.debit or line.credit, decimal_sep="."),
                    fh.zero_pad(0, 8),
                    fh.clean_text(line.name or move.ref, 200, sep=","),
                    fh.clean_text(move.ref, 20, sep=","),
                    fh.only_digits(line.partner_id.cnpj_cpf),
                    "",
                    "",
                ]
                out.write(fh.join_delimited(campos, ","))
                out.write("\n")
        return [(self._file_name(), self._encode(out.getvalue()))]

    # ------------------------------------------------------------------
    # IGNIS: ponto e virgula, mas cada campo tambem com largura fixa
    # ------------------------------------------------------------------
