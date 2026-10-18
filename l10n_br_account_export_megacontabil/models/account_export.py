# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_megacontabil(self):
        """Mega Contabil: registros curtos com prefixo numerico.

        Referencia: 00MEGACONTABIL / 01<CNPJ formatado> / linhas de lancamento.
        """
        out = self._new_buffer()
        out.write("00MEGACONTABIL\n")
        out.write("01" + (self.company_id.cnpj_cpf or "") + "\n")
        for move in self.move_ids:
            for conta_d, conta_c, valor, hist, data in self._pair_entries(move):
                linha = (
                    "02"
                    + fh.format_date(data, "%d%m%Y")
                    + fh.pad(conta_d, 15)
                    + fh.pad(conta_c, 15)
                    + fh.pad(fh.format_amount(valor), 15, align=fh.ALIGN_RIGHT)
                    + fh.pad(fh.clean_text(hist, 100), 100)
                )
                out.write(linha + "\n")
        return [(self._file_name(), self._encode(out.getvalue()))]
