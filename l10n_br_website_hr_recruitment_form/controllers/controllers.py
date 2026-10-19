# (c) 2024 Kmee - Felipe Zago <felipe.zago@kmee.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import http
from odoo.http import request
from odoo.tools import consteq

# Only these keys of the submitted payload are written on the applicant: the
# endpoint is public, so everything else (stage, salary, token...) is ignored.
APPLICATION_FIELDS = {
    "name",
    "birthday",
    "rg",
    "cnpj_cpf",
    "ethnicity",
    "nationality_id",
    "partner_phone",
    "email_from",
    "father_name",
    "mother_name",
    "creservist",
    "pis_pasep",
    "certificate",
    "voter_title",
    "voter_zone",
    "voter_section",
    "rg_file",
    "cnh_file",
    "voter_title_file",
    "study_proof_file",
    "address_proof_file",
    "reservist_file",
    "pis_file",
    "partner_legal_name",
    "start_date",
    "notes",
    "company_responsible_document",
    "latest_social_contract",
    "address",
    "bank",
    "dependents",
}
ADDRESS_FIELDS = {"street", "street_number", "street2", "district", "zip"}
BANK_FIELDS = {"bank_id", "bra_number", "acc_number"}


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
        if not applicant_sudo or not self._valid_token(applicant_sudo, access_token):
            raise request.not_found()

        banks = request.env["res.bank"].sudo().search([])
        if applicant_sudo.job_id.contract_type_id.regime == "PJ":
            return request.render(
                "l10n_br_website_hr_recruitment_form"
                ".hr_application_company_form_portal_template",
                {
                    "applicant": applicant_sudo,
                    "banks": banks,
                    "access_token": access_token,
                },
            )

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
        ["/application/<int:applicant_id>/form/submit"], type="jsonrpc", auth="public"
    )
    def portal_application_form_submit(
        self, applicant_id, *args, access_token=None, **kwargs
    ):
        applicant_sudo = (
            request.env["hr.applicant"].sudo().browse(applicant_id).exists()
        )
        if not applicant_sudo or not self._valid_token(applicant_sudo, access_token):
            return False

        kwargs = {k: v for k, v in kwargs.items() if k in APPLICATION_FIELDS}
        application_data = self.parse_form_data_to_application_data(kwargs)
        if "address" in application_data:
            if not applicant_sudo.address_home_id:
                applicant_sudo.address_home_id = (
                    request.env["res.partner"]
                    .sudo()
                    .create({"name": applicant_sudo.partner_name})
                )
            applicant_sudo.address_home_id.sudo().write(
                self._prepare_address_values(application_data["address"])
            )
            del application_data["address"]

        if "bank" in application_data:
            if not applicant_sudo.bank_account_id:
                applicant_sudo.bank_account_id = (
                    request.env["res.partner.bank"]
                    .sudo()
                    .create({"partner_id": applicant_sudo.address_home_id.id})
                )
            bank_values = {
                key: value
                for key, value in application_data["bank"].items()
                if key in BANK_FIELDS
            }
            bank_values["bank_id"] = int(bank_values.get("bank_id") or 0)
            applicant_sudo.bank_account_id.sudo().write(bank_values)
            del application_data["bank"]

        applicant_sudo.write(application_data)
        return True

    @staticmethod
    def _valid_token(applicant_sudo, access_token):
        return bool(access_token) and consteq(applicant_sudo.access_token, access_token)

    def _prepare_address_values(self, address):
        """Map the form address to res.partner values.

        The form sends the street as ``street`` (a computed field of the
        partner) and city/state as typed names, not ids.
        """
        values = {k: v for k, v in address.items() if k in ADDRESS_FIELDS}
        if "street" in values:
            values["street_name"] = values.pop("street")
        env = request.env
        state = False
        state_name = (address.get("state_id") or "").strip()
        if state_name:
            state = (
                env["res.country.state"]
                .sudo()
                .search(
                    [
                        ("country_id.code", "=", "BR"),
                        "|",
                        ("code", "=ilike", state_name),
                        ("name", "=ilike", state_name),
                    ],
                    limit=1,
                )
            )
            if state:
                values["state_id"] = state.id
        city_name = (address.get("city_id") or "").strip()
        if city_name:
            domain = [("name", "=ilike", city_name)]
            if state:
                domain.append(("state_id", "=", state.id))
            city = env["res.city"].sudo().search(domain, limit=1)
            if city:
                values["city_id"] = city.id
        return values

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
