# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestL10nBrHrRecruitment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Candidate Partner",
                "country_id": cls.env.ref("base.br").id,
                "l10n_br_rg_code": "123456789",
            }
        )
        cls.applicant = cls.env["hr.applicant"].create(
            {
                "name": "Candidate",
                "partner_name": "Candidate Partner",
                "partner_id": cls.partner.id,
                "pis_pasep": "12345678900",
                "father_name": "Father",
                "mother_name": "Mother",
                "dependent_ids": [
                    (0, 0, {"name": "Kid", "date_of_birth": "2020-01-01"})
                ],
            }
        )

    def test_related_fields_follow_partner(self):
        self.assertEqual(self.applicant.nationality_id, self.env.ref("base.br"))
        self.assertEqual(self.applicant.rg, "123456789")

    def test_create_employee_from_applicant(self):
        action = self.applicant.create_employee_from_applicant()
        employee = self.env["hr.employee"].browse(action["res_id"])
        self.assertEqual(employee.pis_pasep, "12345678900")
        self.assertEqual(employee.father_name, "Father")
        self.assertEqual(employee.mother_name, "Mother")
        self.assertEqual(employee.country_id, self.env.ref("base.br"))
        self.assertEqual(employee.relative_ids.name, "Kid")

    def test_contract_type_default_regime(self):
        contract_type = self.env["hr.contract.type"].create({"name": "Test type"})
        self.assertEqual(contract_type.regime, "CLT")
