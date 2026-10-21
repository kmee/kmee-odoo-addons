from odoo import fields, models


class JobShareWizard(models.TransientModel):
    _name = "job.share.wizard"
    _description = "Job Share Wizard"

    job_id = fields.Many2one("hr.job", string="Vaga", required=True, readonly=True)
    application_url = fields.Char(
        "URL da Vaga", related="job_id.application_url", store=False
    )
