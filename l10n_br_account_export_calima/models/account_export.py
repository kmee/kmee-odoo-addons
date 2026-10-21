# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_calima(self):
        """Calima ERP: registro 00 de abertura e 301 por partida."""
        out = self._new_buffer()
        cabecalho = (
            fh.zero_pad(2, 8)
            + fh.format_date(self.date_end)
            + fh.only_digits(self.company_id.cnpj_cpf)
            + fh.format_date(self.date_start)
            + fh.format_date(self.date_end)
            + fh.pad("Arquivo de integracao dos lancamentos contabeis.", 100)
        )
        out.write(fh.pad(cabecalho, 252) + "\n")
        for move in self.move_ids:
            for conta_d, conta_c, valor, hist, data in self._pair_entries(move):
                linha = (
                    "301"
                    + fh.format_date(data)
                    + "R"
                    + fh.pad(conta_d, 18)
                    + fh.pad(conta_c, 18)
                    + fh.amount_cents(valor, 9)
                    + fh.pad(fh.clean_text(hist, 200), 200)
                )
                out.write(fh.pad(linha, 597) + "\n")
        return [(self._file_name(), self._encode(out.getvalue()))]
