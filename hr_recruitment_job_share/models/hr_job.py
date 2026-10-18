import secrets

from odoo import api, fields, models


class Job(models.Model):
    _inherit = "hr.job"

    access_token = fields.Char(
        "Token de Acesso", copy=False, default=lambda self: secrets.token_urlsafe(16)
    )
    is_shared = fields.Boolean("É compartilhado?", default=False)
    application_url = fields.Char("URL da Vaga", compute="_compute_application_url")

    def get_share_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return f"{base_url}/jobs/details/{self.id}?access_token={self.access_token}"

    @api.depends("access_token")
    def _compute_application_url(self):
        for job in self:
            job.application_url = job.get_share_url() if job.access_token else ""

    def action_share_job(self):
        self.ensure_one()
        # Gerar um novo token ao compartilhar o trabalho
        self.access_token = secrets.token_urlsafe(16)  # Garante que cada token é único
        self.is_shared = True
        return {
            "type": "ir.actions.act_window",
            "res_model": "job.share.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_job_id": self.id},
        }

    @api.model
    def create(self, vals):
        # Garante que o token de acesso é gerado no momento da criação
        if "access_token" not in vals:
            vals["access_token"] = secrets.token_urlsafe(16)
        return super(Job, self).create(vals)

    def write(self, vals):
        # Se o trabalho não estiver sendo compartilhado, não altere o token
        if "is_shared" in vals and vals["is_shared"]:
            self.access_token = secrets.token_urlsafe(16)
        return super(Job, self).write(vals)
