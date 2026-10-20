# Copyright 2019 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class SacPrint(models.TransientModel):

    _name = "sac.print"
    _description = "sac print"

    name = fields.Char()

    def doit(self):
        self.ensure_one()

        to_print = self.env["sac"].search(
            [
                ("stage_id", "=", self.env.ref("sac.sac_kanban_aguardando_envio").id),
                ("is_printed", "=", False),
            ]
        )

        if to_print:
            report = self.env["ir.actions.report"]._get_report_from_name(
                "sac.sac_declaracao_conteudo"
            )
            if not report:
                raise UserError(
                    _("The report 'sac.sac_declaracao_conteudo' is not installed.")
                )
            to_print.write({"is_printed": True})
            return report.report_action(to_print)
        return False
