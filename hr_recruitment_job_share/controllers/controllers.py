from odoo import http
from odoo.http import request
from odoo.osv.expression import OR
from odoo.tools.translate import _


class JobShareController(http.Controller):
    @http.route(
        ["/jobs", "/jobs/page/<int:page>"],
        type="http",
        auth="public",
        website=True,
    )
    def list_jobs(
        self,
        page=1,
        date_begin=None,
        date_end=None,
        sortby=None,
        search=None,
        search_in="name",
        **kw
    ):
        domain = []

        searchbar_sortings = {
            "date": {"label": _("Newest"), "order": "create_date desc"},
            "name": {"label": _("Name"), "order": "name"},
        }

        searchbar_inputs = {
            "name": {
                "input": "name",
                "label": _('Search <span class="nolabel"> (in Name)</span>'),
            },
            "all": {"input": "all", "label": _("Search in All")},
        }

        if not sortby:
            sortby = "date"
        order = searchbar_sortings[sortby]["order"]

        if date_begin and date_end:
            domain += [
                ("create_date", ">", date_begin),
                ("create_date", "<=", date_end),
            ]

        if search and search_in:
            search_domain = []
            if search_in in ("name", "all"):
                search_domain = OR([search_domain, [("name", "ilike", search)]])
            domain += search_domain

        hr_job_count = request.env["hr.job"].search_count(domain)
        items_per_page = 10
        pager = request.website.pager(
            url="/jobs",
            total=hr_job_count,
            page=page,
            step=items_per_page,
        )

        hr_jobs = request.env["hr.job"].search(
            domain, order=order, limit=items_per_page, offset=pager["offset"]
        )

        values = {
            "date": date_begin,
            "hr_jobs": hr_jobs,
            "pager": pager,
            "searchbar_sortings": searchbar_sortings,
            "searchbar_inputs": searchbar_inputs,
            "sortby": sortby,
            "search_in": search_in,
            "search": search,
        }

        return request.render("website_hr_recruitment.detail", values)

    @http.route(
        ["/jobs/details/<int:hr_job_id>"], type="http", auth="public", website=True
    )
    def job_followup(self, hr_job_id=None, access_token=None, **kw):

        hr_job_sudo = (
            request.env["hr.job"].sudo().search([("id", "=", hr_job_id)], limit=1)
        )

        values = {"page_name": "hr_job", "job": hr_job_sudo}
        return request.render("website_hr_recruitment.detail", values)

    @http.route(
        ["/jobs/apply/<int:hr_job_id>"], type="http", auth="public", website=True
    )
    def job_apply(self, hr_job_id=None, **kw):

        hr_job_sudo = (
            request.env["hr.job"].sudo().search([("id", "=", hr_job_id)], limit=1)
        )

        values = {"job": hr_job_sudo}
        return request.render("website_hr_recruitment.apply", values)
