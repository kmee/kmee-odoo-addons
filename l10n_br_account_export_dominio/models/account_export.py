# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_dominio(self):
        """Layout Dominio: 0000 (empresa), 6000 (lancamento), 6100 (partidas).

        Estrutura conferida contra arquivo real. O 6100 traz debito e credito na
        MESMA linha; em partidas multiplas a conta "0" marca o lado rateado.
        """
        out = self._new_buffer()
        cnpj = fh.only_digits(self.company_id.cnpj_cpf)
        out.write(fh.join_delimited(["0000", cnpj], "|", leading=True, trailing=True))
        out.write("\n")
        for move in self.move_ids:
            debitos, creditos = self._split_sides(move)
            if not debitos or not creditos:
                continue
            out.write(
                fh.join_delimited(
                    ["6000", "X", "", "", ""], "|", leading=True, trailing=True
                )
            )
            out.write("\n")
            for conta_d, conta_c, valor, hist, data in self._pair_entries(
                move, rateio="0"
            ):
                campos = [
                    "6100",
                    fh.format_date(data),
                    conta_d,
                    conta_c,
                    fh.format_amount(valor),
                    "",
                    fh.clean_text(hist, 512, sep="|"),
                    "",
                    "",
                    "",
                ]
                out.write(fh.join_delimited(campos, "|", leading=True, trailing=True))
                out.write("\n")
        return [(self._file_name(), self._encode(out.getvalue()))]

    # ------------------------------------------------------------------
    # Alterdata WCont: CSV com aspas, uma linha por partida
    # ------------------------------------------------------------------
