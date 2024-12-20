# (c) 2024 Kmee - Felipe Zago <felipe.zago@kmee.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import http
from odoo.http import request


class HRApplicationController(http.Controller):
    @http.route(
        ["/application/<int:applicant_id>/form"],
        type="http",
        auth="public",
        access_token=None,
        website=True,
    )
    def portal_application_form(
        self,
        applicant_id,
        access_token=None,
    ):
        applicant_sudo = (
            request.env["hr.applicant"].sudo().browse(applicant_id).exists()
        )
        if not applicant_sudo or applicant_sudo.access_token != access_token:
            return request.render("website.page_404")

        banks = request.env["res.bank"].sudo().search([])
        countries = request.env["res.country"].sudo().search([])
        ethnicities = request.env["hr.ethnicity"].sudo().search([])
        return request.render(
            "l10n_br_website_hr_recruitment_form.hr_application_form_portal_template",
            {
                "applicant": applicant_sudo,
                "countries": countries,
                "ethnicities": ethnicities,
                "banks": banks,
                "access_token": access_token,
            },
        )

    @http.route(
        ["/application/<int:applicant_id>/form/submit"], type="json", auth="public"
    )
    def portal_application_form_submit(self, applicant_id, *args, **kwargs):
        applicant_sudo = (
            request.env["hr.applicant"].sudo().browse(applicant_id).exists()
        )
        if not applicant_sudo:
            return False

        application_data = self.parse_form_data_to_application_data(kwargs)
        if "address" in application_data:
            if not applicant_sudo.address_home_id:
                applicant_sudo.address_home_id = request.env["res.partner"].create(
                    {"name": applicant_sudo.partner_name}
                )
            applicant_sudo.address_home_id.sudo().write(application_data["address"])
            del application_data["address"]

        if "bank" in application_data:
            if not applicant_sudo.bank_account_id:
                applicant_sudo.bank_account_id = request.env["res.partner.bank"].create(
                    {"partner_id": applicant_sudo.address_home_id.id}
                )
            application_data["bank"]["bank_id"] = int(
                application_data["bank"]["bank_id"]
            )
            applicant_sudo.bank_account_id.sudo().write(application_data["bank"])
            del application_data["bank"]

        applicant_sudo.write(application_data)
        return True

    def parse_form_data_to_application_data(self, data):
        applicantion_data = {}
        for field_name, value in data.items():
            if field_name == "dependents":
                field_name = "dependent_ids"
                value = self.parse_dependants(value)

            if field_name == "nationality_id" or field_name == "ethnicity":
                value = int(value)

            applicantion_data[field_name] = value

        return applicantion_data

    def parse_dependants(self, dependants):
        value = [(5, 0, 0)]
        for dep in dependants:
            value.append(
                (0, 0, {"name": dep["name"], "date_of_birth": dep["date_of_birth"]})
            )

        return value
