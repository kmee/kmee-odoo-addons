from odoo import api, fields, models

class ProjectProject(models.Model):
    _inherit = "project.project"

    root_folder_id = fields.Many2one(
        "project.folder", string="Pasta Raiz", ondelete="set null", copy=False
    )
    folder_count = fields.Integer(
        compute="_compute_folder_count", string="Pastas", store=False
    )

    def _compute_folder_count(self):
        Folder = self.env["project.folder"]
        for proj in self:
            proj.folder_count = Folder.search_count([("project_id", "=", proj.id)])

    def action_open_folders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Pastas – {self.display_name}",
            "res_model": "project.folder",
            "view_mode": "kanban,tree,form",
            "domain": [("project_id", "=", self.id), ("parent_id", "=", False)],
            "context": {
                "default_project_id": self.id,
            },
        }

    def action_open_all_folders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Todas as Pastas – {self.display_name}",
            "res_model": "project.folder",
            "view_mode": "tree,kanban,form",
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        # cria pasta raiz
        root = self.env["project.folder"].create({
            "name": "Documentos do Projeto",
            "project_id": rec.id,
        })
        rec.root_folder_id = root.id
        return rec
