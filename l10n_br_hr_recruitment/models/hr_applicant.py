# (c) 2024 Kmee - Felipe Zago <felipe.zago@kmee.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    birthday = fields.Date("Date of Birth", groups="hr.group_hr_user", tracking=True)

    address_home_id = fields.Many2one(
        "res.partner",
        "Address",
        help="Enter here the private address of the applicant",
        groups="hr.group_hr_user",
        tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    nationality_id = fields.Many2one(
        string="Nationality",
        store=True,
        related="address_home_id.country_id",
        readonly=False,
        groups="hr.group_hr_user",
    )

    ethnicity = fields.Many2one(comodel_name="hr.ethnicity", groups="hr.group_hr_user")

    father_name = fields.Char(groups="hr.group_hr_user")

    mother_name = fields.Char(groups="hr.group_hr_user")

    voter_title = fields.Char(groups="hr.group_hr_user")

    voter_zone = fields.Char(groups="hr.group_hr_user")

    voter_section = fields.Char(groups="hr.group_hr_user")

    rg = fields.Char(
        string="RG",
        store=True,
        readonly=False,
        related="address_home_id.inscr_est",
        help="National ID number",
        groups="hr.group_hr_user",
    )

    cnpj_cpf = fields.Char(
        string="CPF",
        store=True,
        related="address_home_id.cnpj_cpf",
        readonly=False,
        groups="hr.group_hr_user",
    )

    creservist = fields.Char(
        string="Military service status certificate", groups="hr.group_hr_user"
    )

    pis_pasep = fields.Char(string="PIS/PASEP", groups="hr.group_hr_user")

    bank_account_id = fields.Many2one(
        "res.partner.bank",
        "Bank Account Number",
        domain="""[
            ('partner_id', '=', address_home_id),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', company_id)]
        """,
        groups="hr.group_hr_user",
        tracking=True,
    )

    driver_license = fields.Char(
        string="Driver license number", groups="hr.group_hr_user"
    )

    driver_categ = fields.Char(
        string="Driver license category", groups="hr.group_hr_user"
    )

    expiration_date = fields.Date(groups="hr.group_hr_user")

    certificate = fields.Selection(
        [
            ("graduate", "Graduate"),
            ("bachelor", "Bachelor"),
            ("master", "Master"),
            ("doctor", "Doctor"),
            ("other", "Other"),
        ],
        "Certificate Level",
        default="other",
        groups="hr.group_hr_user",
        tracking=True,
    )

    study_field = fields.Char(
        "Field of Study", groups="hr.group_hr_user", tracking=True
    )

    study_school = fields.Char("School", groups="hr.group_hr_user", tracking=True)

    rg_file = fields.Binary(string="RG File")

    cnh_file = fields.Binary(string="CNH File")

    voter_title_file = fields.Binary()

    reservist_file = fields.Binary()

    address_proof_file = fields.Binary()

    study_proof_file = fields.Binary()

    pis_file = fields.Binary()

    dependent_ids = fields.One2many(
        comodel_name="hr.applicant.dependent",
        inverse_name="applicant_id",
    )

    # specific company applicant data
    partner_legal_name = fields.Char()

    company_responsible_document = fields.Binary()

    latest_social_contract = fields.Binary()

    start_date = fields.Date()

    notes = fields.Text()

    def create_employee_from_applicant(self):
        res = super().create_employee_from_applicant()

        res["context"] = {
            **res["context"],
            "default_address_home_id": self.address_home_id.id,
            "default_bank_account_id": self.bank_account_id.id,
            "default_ethnicity": self.ethnicity.id,
            "default_father_name": self.father_name,
            "default_mother_name": self.mother_name,
            "default_voter_title": self.voter_title,
            "default_voter_zone": self.voter_zone,
            "default_voter_section": self.voter_section,
            "default_creservist": self.creservist,
            "default_pis_pasep": self.pis_pasep,
            "default_driver_license": self.driver_license,
            "default_driver_categ": self.driver_categ,
            "default_expiration_date": self.expiration_date,
            "default_certificate": self.certificate,
            "default_study_field": self.study_field,
            "default_study_school": self.study_school,
            "default_rg_file": self.rg_file,
            "default_cnh_file": self.cnh_file,
            "default_voter_title_file": self.voter_title_file,
            "default_reservist_file": self.reservist_file,
            "default_address_proof_file": self.address_proof_file,
            "default_study_proof_file": self.study_proof_file,
            "default_pis_file": self.pis_file,
            "default_relative_ids": [
                (
                    0,
                    0,
                    {
                        "name": dependent.name,
                        "date_of_birth": dependent.date_of_birth,
                        "relation_id": self.env.ref(
                            "hr_employee_relative.relation_child"
                        ).id,
                    },
                )
                for dependent in self.dependent_ids
            ],
        }

        return res


class HrApplicantDependent(models.Model):
    _name = "hr.applicant.dependent"

    applicant_id = fields.Many2one(comodel_name="hr.applicant")

    name = fields.Char(required=True)

    date_of_birth = fields.Date(required=True)
