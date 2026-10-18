from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class JobShareController(http.Controller):
    @http.route(
        ["/jobs/details/<int:hr_job_id>"], type="http", auth="public", website=True
    )
    def job_followup(self, hr_job_id=None, access_token=None, **kw):
        hr_job_sudo = (
            request.env["hr.job"].sudo().search([("id", "=", hr_job_id)], limit=1)
        )

        if not hr_job_sudo or hr_job_sudo.access_token != access_token:
            raise NotFound()

        values = {
            "page_name": "hr_job",
            "job": hr_job_sudo,
            "access_token": access_token,
        }
        return request.render("website_hr_recruitment.detail", values)

    @http.route(
        ["/jobs/apply/<int:hr_job_id>"], type="http", auth="public", website=True
    )
    def job_apply(self, hr_job_id=None, access_token=None, **kw):
        hr_job_sudo = (
            request.env["hr.job"].sudo().search([("id", "=", hr_job_id)], limit=1)
        )

        if not hr_job_sudo or (
            hr_job_sudo.access_token != access_token and not hr_job_sudo.is_published
        ):
            raise NotFound()

        values = {"job": hr_job_sudo}
        return request.render("website_hr_recruitment.apply", values)
