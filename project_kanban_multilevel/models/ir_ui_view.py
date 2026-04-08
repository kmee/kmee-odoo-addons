from odoo import fields, models


class View(models.Model):
    _inherit = "ir.ui.view"

    type = fields.Selection(
        selection_add=[("kanban_multilevel", "Kanban Multilevel")]
    )

    def _is_qweb_based_view(self, view_type):
        return view_type == "kanban_multilevel" or super()._is_qweb_based_view(view_type)

    def _get_view_info(self):
        return {
            "kanban_multilevel": {"icon": "fa fa-th"},
        } | super()._get_view_info()
