from odoo import api, fields, models

class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    project_folder_id = fields.Many2one(
        "project.folder",
        string="Pasta do Projeto",
        ondelete="set null",
        index=True,
    )
    project_id = fields.Many2one(
        related="project_folder_id.project_id",
        store=True,
        readonly=True,
    )

    @api.onchange("res_model", "res_id")
    def _onchange_res_ref_clear_folder(self):
        pass
