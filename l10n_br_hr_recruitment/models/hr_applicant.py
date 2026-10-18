# (c) 2024 Kmee - Felipe Zago <felipe.zago@kmee.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    birthday = fields.Date("Date of Birth", groups="hr.group_hr_user", tracking=True)

    nationality_id = fields.Many2one(
        string="Nationality",
        store=True,
        related="partner_id.country_id",
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
        related="partner_id.l10n_br_rg_code",
        help="National ID number",
        groups="hr.group_hr_user",
    )

    cnpj_cpf = fields.Char(
        string="CPF",
        store=True,
        related="partner_id.vat",
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
            ('partner_id', '=', partner_id),
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

    def _prepare_l10n_br_employee_vals(self):
        self.ensure_one()
        vals = {}
        vals.update(
            {
                "bank_account_id": self.bank_account_id.id,
                "ethnicity": self.ethnicity.id,
                "father_name": self.father_name,
                "mother_name": self.mother_name,
                "voter_title": self.voter_title,
                "voter_zone": self.voter_zone,
                "voter_section": self.voter_section,
                "creservist": self.creservist,
                "pis_pasep": self.pis_pasep,
                "driver_license": self.driver_license,
                "driver_categ": self.driver_categ,
                "expiration_date": self.expiration_date,
                "certificate": self.certificate,
                "study_field": self.study_field,
                "study_school": self.study_school,
                "rg_file": self.rg_file,
                "cnh_file": self.cnh_file,
                "voter_title_file": self.voter_title_file,
                "reservist_file": self.reservist_file,
                "address_proof_file": self.address_proof_file,
                "study_proof_file": self.study_proof_file,
                "pis_file": self.pis_file,
                "relative_ids": [
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
        )
        if self.nationality_id:
            vals["country_id"] = self.nationality_id.id
        return vals

    def create_employee_from_applicant(self):
        # Odoo 18 builds the employee from hr.candidate, so the Brazilian
        # applicant data is written on the created employee afterwards.
        action = super().create_employee_from_applicant()
        employee = self.env["hr.employee"].browse(action["res_id"])
        employee.write(self._prepare_l10n_br_employee_vals())
        return action


class HrApplicantDependent(models.Model):
    _name = "hr.applicant.dependent"
    _description = "Applicant Dependent"

    applicant_id = fields.Many2one(comodel_name="hr.applicant")

    name = fields.Char(required=True)

    date_of_birth = fields.Date(required=True)
