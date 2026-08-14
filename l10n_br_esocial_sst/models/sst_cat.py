# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class L10nBrSstCat(models.Model):
    """Liga a CAT ao evento S-2210 e traz o recibo de volta para ela."""

    _inherit = "l10n_br.sst.cat"

    s2210_id = fields.Many2one(
        "l10n_br.esocial.s2210",
        string="Evento S-2210",
        readonly=True,
        copy=False,
    )
    esocial_evento_id = fields.Many2one(
        related="s2210_id.evento_id",
        string="Evento eSocial",
        readonly=True,
    )
    esocial_state = fields.Selection(
        related="s2210_id.evento_id.state",
        string="Situação no eSocial",
        readonly=True,
    )

    def action_gerar_s2210(self):
        """Cria o intermediário do S-2210 desta CAT."""
        self.ensure_one()
        if self.s2210_id:
            return self.s2210_id
        self.s2210_id = self.env["l10n_br.esocial.s2210"].create(
            {
                "company_id": self.company_id.id,
                "employee_id": self.employee_id.id,
                "cat_id": self.id,
            }
        )
        return self.s2210_id

    def action_emitir(self):
        """Emitir a CAT já prepara o evento que a comunica de fato."""
        res = super().action_emitir()
        for rec in self:
            rec.action_gerar_s2210()
        return res

    @api.model
    def _atualizar_recibo(self):
        """Copia para a CAT o recibo devolvido pelo eSocial."""
        for rec in self.search([("s2210_id", "!=", False)]):
            recibo = rec.s2210_id.evento_id.nr_recibo
            if recibo and rec.numero_recibo != recibo:
                rec.write({"numero_recibo": recibo, "state": "transmitida"})
        return True

    def action_view_s2210(self):
        self.ensure_one()
        return {
            "name": _("S-2210"),
            "type": "ir.actions.act_window",
            "res_model": "l10n_br.esocial.s2210",
            "view_mode": "form",
            "res_id": self.s2210_id.id,
        }
