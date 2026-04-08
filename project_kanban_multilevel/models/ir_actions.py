from odoo import fields, models


class ActWindowView(models.Model):
    _inherit = "ir.actions.act_window.view"

    view_mode = fields.Selection(
        selection_add=[("kanban_multilevel", "Kanban Multilevel")],
        ondelete={"kanban_multilevel": "cascade"},
    )
