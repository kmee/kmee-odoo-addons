from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    van_session_id = fields.Many2one("van.session", index=True)
    van_type = fields.Selection(
        [("load", "Carga"), ("unload", "Descarga")],
    )

    def button_validate(self):
        res = super().button_validate()
        for picking in self:
            if not picking.van_session_id:
                continue
            if picking.van_type == "load":
                picking.van_session_id._on_load_picking_validated()
            elif picking.van_type == "unload":
                picking.van_session_id._update_in_move_lines()
        return res
