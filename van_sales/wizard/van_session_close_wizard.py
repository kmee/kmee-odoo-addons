from odoo import api, fields, models


class VanSessionCloseWizard(models.TransientModel):
    _name = "van.session.close.wizard"
    _description = "Wizard de Fechamento de Sessão Van"

    session_id = fields.Many2one("van.session", required=True, readonly=True)
    line_ids = fields.One2many(
        "van.session.close.wizard.line", "wizard_id", string="Linhas"
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        session_id = self.env.context.get("active_id")
        if session_id:
            session = self.env["van.session"].browse(session_id)
            lines = []
            for line in session.line_ids:
                qty_remaining = line.qty_out - line.qty_sold
                if qty_remaining <= 0:
                    continue
                lines.append(
                    (
                        0,
                        0,
                        {
                            "session_line_id": line.id,
                            "product_id": line.product_id.id,
                            "qty_out": line.qty_out,
                            "qty_sold": line.qty_sold,
                            "qty_remaining": qty_remaining,
                            "return_to": "van",
                        },
                    )
                )
            res.update(
                {
                    "session_id": session.id,
                    "line_ids": lines,
                }
            )
        return res

    def action_return_all(self):
        """Set return_to='warehouse' on all lines (return everything to WH)."""
        self.line_ids.write({"return_to": "warehouse"})
        return self._reopen()

    def action_keep_all(self):
        """Set return_to='van' on all lines (keep everything in van)."""
        self.line_ids.write({"return_to": "van"})
        return self._reopen()

    def _reopen(self):
        """Reopen the same wizard to reflect changes."""
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_confirm(self):
        """Apply return_to decisions to session lines, then close the session."""
        self.ensure_one()
        session = self.session_id
        for wiz_line in self.line_ids:
            if wiz_line.return_to == "van":
                wiz_line.session_line_id.qty_keep = wiz_line.qty_remaining
            else:
                wiz_line.session_line_id.qty_keep = 0
        session.action_post()
        return {"type": "ir.actions.act_window_close"}


class VanSessionCloseWizardLine(models.TransientModel):
    _name = "van.session.close.wizard.line"
    _description = "Linha do Wizard de Fechamento"

    wizard_id = fields.Many2one(
        "van.session.close.wizard", required=True, ondelete="cascade"
    )
    session_line_id = fields.Many2one("van.session.line", required=True, readonly=True)
    product_id = fields.Many2one("product.product", string="Produto", readonly=True)
    qty_out = fields.Float(string="Saída", readonly=True)
    qty_sold = fields.Float(string="Vendida", readonly=True)
    qty_remaining = fields.Float(string="Sobra", readonly=True)
    return_to = fields.Selection(
        [
            ("van", "Manter no Caminhão"),
            ("warehouse", "Devolver ao Armazém"),
        ],
        string="Destino",
        default="van",
        required=True,
    )
