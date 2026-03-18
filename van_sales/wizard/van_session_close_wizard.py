from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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
                            "qty_keep": line.qty_keep,
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
        """Set qty_keep=0 on all lines (return everything to WH)."""
        self.line_ids.write({"qty_keep": 0})
        return self._reopen()

    def action_keep_all(self):
        """Set qty_keep=qty_remaining on all lines (keep everything in van)."""
        for line in self.line_ids:
            line.qty_keep = line.qty_remaining
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
        """Apply qty_keep to session lines, then close the session."""
        self.ensure_one()
        session = self.session_id
        for wiz_line in self.line_ids:
            wiz_line.session_line_id.qty_keep = wiz_line.qty_keep
        # Reset qty_keep for lines not in wizard (fully sold) — already 0
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
    qty_keep = fields.Float(string="Manter no Caminhão")

    @api.constrains("qty_keep", "qty_remaining")
    def _check_qty_keep(self):
        for line in self:
            if line.qty_keep < 0:
                raise ValidationError(_("A quantidade a manter não pode ser negativa."))
            if line.qty_keep > line.qty_remaining:
                raise ValidationError(
                    _(
                        "A quantidade a manter (%(qty_keep)s) não pode exceder"
                        " a sobra (%(remaining)s) para o produto %(product)s."
                    )
                    % {
                        "qty_keep": line.qty_keep,
                        "remaining": line.qty_remaining,
                        "product": line.product_id.display_name,
                    }
                )
