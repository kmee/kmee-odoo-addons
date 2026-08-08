# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.l10n_br_account_export.models import format_helper as fh


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_dominio_completo(self):
        """Dominio com plano de contas: 0000, 0200 (contas) e os lancamentos.

        Enviar o plano junto e o que costuma garantir importacao sem ajuste
        manual, porque as contas passam a existir no destino.
        """
        arquivos = self._generate_dominio()
        out = self._new_buffer()
        contas = self._get_export_lines().account_id
        for conta in contas.sorted("code"):
            campos = [
                "0200",
                conta.l10n_br_export_code or "",
                "1",
                "A",
                fh.clean_text(conta.name, 60, sep="|"),
                fh.format_date(self.date_start),
                "A",
                "",
                "",
                "",
                "",
                "",
            ]
            out.write(fh.join_delimited(campos, "|", leading=True, trailing=True))
            out.write("\n")
        arquivos.append(
            (
                self._file_name(sufixo="plano_contas"),
                self._encode(out.getvalue()),
            )
        )
        return arquivos
