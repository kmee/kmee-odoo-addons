from odoo import api, fields, models


class ProjectFolder(models.Model):
    _name = "project.folder"
    _description = "Project Folder"
    _order = "sequence, name"
    _parent_name = "parent_id"
    _parent_store = True

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one("project.project", required=True, ondelete="cascade")
    parent_id = fields.Many2one("project.folder", string="Pasta pai", ondelete="restrict")
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("project.folder", "parent_id", string="Subpastas")

    attachment_ids = fields.One2many(
        "ir.attachment", "project_folder_id", string="Arquivos"
    )
    attachment_count = fields.Integer(compute="_compute_attachment_count", store=False)
    full_path = fields.Char(compute="_compute_full_path", store=False)

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec.attachment_ids)

    @api.depends("name", "parent_id", "parent_id.full_path", "project_id.name")
    def _compute_full_path(self):
        for rec in self:
            parts = []
            # opcional incluir nome do projeto
            if rec.project_id:
                parts.append(rec.project_id.display_name)
            # sobe a hierarquia
            node = rec
            chain = []
            while node:
                chain.append(node.name or "")
                node = node.parent_id
            parts.extend(reversed(chain))
            rec.full_path = " / ".join([p for p in parts if p])
