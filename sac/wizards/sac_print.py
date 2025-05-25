# Copyright 2019 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


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
            to_print.write({"is_printed": True})
            return self.env["report"].get_action(
                to_print, "sac.sac_declaracao_conteudo"
            )
        return False
