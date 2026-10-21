# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

from lxml import etree

from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestApplicationForm(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.clt = cls.env["hr.contract.type"].create(
            {"name": "CLT test", "regime": "CLT"}
        )
        cls.pj = cls.env["hr.contract.type"].create({"name": "PJ test", "regime": "PJ"})
        cls.job = cls.env["hr.job"].create(
            {"name": "Analista", "contract_type_id": cls.clt.id}
        )
        cls.job_pj = cls.env["hr.job"].create(
            {"name": "Consultor", "contract_type_id": cls.pj.id}
        )
        # 19.0: name and e-mail are back on the application (no hr.candidate)
        cls.applicant = cls.env["hr.applicant"].create(
            {
                "partner_name": "Maria Candidata",
                "email_from": "maria@example.com",
                "job_id": cls.job.id,
            }
        )
        cls.applicant_pj = cls.env["hr.applicant"].create(
            {"partner_name": "Consultoria PJ", "job_id": cls.job_pj.id}
        )
        cls.state = cls.env["res.country.state"].search(
            [("code", "=", "SP"), ("country_id.code", "=", "BR")], limit=1
        )
        cls.bank = cls.env["res.bank"].create({"name": "Banco Teste", "bic": "BTST"})
        cls.city = cls.env["res.city"].create(
            {
                "name": "Campinas Teste",
                "state_id": cls.state.id,
                "country_id": cls.state.country_id.id,
            }
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _form_url(self, applicant, token="default"):
        if token == "default":
            token = applicant.access_token
        return "/application/%d/form?access_token=%s" % (applicant.id, token or "")

    def _submit(self, applicant, token="default", **params):
        if token == "default":
            token = applicant.access_token
        if token is not None:
            params["access_token"] = token
        response = self.url_open(
            "/application/%d/form/submit" % applicant.id,
            data=json.dumps({"jsonrpc": "2.0", "method": "call", "params": params}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json().get("result")

    # ------------------------------------------------------------------
    # applicant model
    # ------------------------------------------------------------------
    def test_each_applicant_has_its_own_access_token(self):
        """
        Given two applicants
        When they are created (and one is duplicated)
        Then every one has a different non-empty security token
        """
        copy = self.applicant.copy()
        tokens = {
            self.applicant.access_token,
            self.applicant_pj.access_token,
            copy.access_token,
        }
        self.assertEqual(len(tokens), 3)
        self.assertTrue(all(tokens))

    def test_form_url_carries_applicant_id_and_token(self):
        """
        Given an applicant
        When its form url is computed
        Then it points to /application/<id>/form with the access token
        """
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        expected = "%s/application/%d/form?access_token=%s" % (
            base,
            self.applicant.id,
            self.applicant.access_token,
        )
        self.assertEqual(self.applicant.form_url, expected)
        self.assertEqual(self.applicant.get_share_url(), expected)

    def test_share_action_sends_the_form_link_to_the_applicant(self):
        """
        Given an applicant with e-mail
        When the 'Share Applicant Form' action runs
        Then an e-mail with the form link is sent to the applicant and the
        message is logged on the applicant
        """
        # 19.0: mail.mail skips sending during tests unless _disable_send is
        # patched on the registry class (no SMTP connection either), as the
        # core mail tests do
        mail_server_cls = type(self.env["ir.mail_server"])
        with patch.object(
            mail_server_cls, "_disable_send", lambda _: False
        ), patch.object(mail_server_cls, "_connect__", return_value=None), patch.object(
            mail_server_cls, "send_email", return_value="<msg-id>"
        ) as send_email:
            self.applicant.action_share_applicant_form()
        self.assertTrue(send_email.called)
        email = send_email.call_args.args[0]
        self.assertIn("maria@example.com", email["To"])
        body = email.get_body().get_content()
        self.assertIn("/application/%d/form?access_token=" % self.applicant.id, body)
        self.assertIn(self.applicant.access_token, body)
        message = self.applicant.message_ids[:1]
        self.assertEqual(message.subject, "Applicant Form")

    def test_share_button_is_in_applicant_form_for_closed_applications(self):
        """
        Given the applicant form view
        When it is built
        Then the header has the share button, hidden until the application is closed
        """
        arch = self.env["hr.applicant"].get_view(view_type="form")["arch"]
        root = etree.fromstring(arch.encode())
        buttons = root.xpath("//header/button[@name='action_share_applicant_form']")
        self.assertEqual(len(buttons), 1)
        self.assertIn("date_closed", buttons[0].get("invisible"))

    # ------------------------------------------------------------------
    # GET form
    # ------------------------------------------------------------------
    def test_clt_applicant_gets_the_personal_form(self):
        """
        Given a CLT job applicant and a valid token
        When the public form is requested
        Then the personal data form is rendered (with personal sections)
        """
        response = self.url_open(self._form_url(self.applicant))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Applicant Data", response.text)
        self.assertIn("Personal Information", response.text)
        self.assertIn("Bank Data", response.text)
        self.assertIn('id="father_name"', response.text)

    def test_pj_applicant_gets_the_company_form(self):
        """
        Given a PJ job applicant and a valid token
        When the public form is requested
        Then the company form is rendered, not the personal one
        """
        response = self.url_open(self._form_url(self.applicant_pj))
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="partner_legal_name"', response.text)
        self.assertNotIn('id="father_name"', response.text)

    def test_form_with_wrong_or_missing_token_is_404(self):
        """
        Given an applicant
        When the form is requested with a wrong token, no token or an unknown id
        Then a 404 page is returned and no applicant data is shown
        """
        for url in (
            self._form_url(self.applicant, token="not-the-token"),
            self._form_url(self.applicant, token=""),
            "/application/999999999/form?access_token=x",
        ):
            response = self.url_open(url)
            self.assertEqual(response.status_code, 404, url)
            self.assertNotIn("Personal Information", response.text)

    # ------------------------------------------------------------------
    # POST submit
    # ------------------------------------------------------------------
    def test_submit_saves_personal_data_address_bank_and_dependents(self):
        """
        Given a CLT applicant with a valid token
        When the personal form is submitted with address, bank and 2 dependents
        Then the data lands on the applicant, its address partner (created on
        demand), its bank account and the dependent lines
        """
        result = self._submit(
            self.applicant,
            father_name="Pai Candidato",
            mother_name="Mae Candidata",
            pis_pasep="123.45678.90-1",
            certificate="bachelor",
            address={
                "street": "Rua das Flores",
                "street_number": "100",
                "district": "Centro",
                "zip": "01001-000",
                "city_id": "campinas teste",
                "state_id": "SP",
            },
            bank={
                "bank_id": self.bank.id,
                "bra_number": "0001",
                "acc_number": "12345-6",
            },
            dependents=[
                {"name": "Filho Um", "date_of_birth": "2015-03-10"},
                {"name": "Filho Dois", "date_of_birth": "2018-07-21"},
            ],
        )
        self.assertTrue(result)
        applicant = self.applicant
        self.assertEqual(applicant.father_name, "Pai Candidato")
        self.assertEqual(applicant.mother_name, "Mae Candidata")
        self.assertEqual(applicant.certificate, "bachelor")
        self.assertEqual(applicant.partner_id.name, "Maria Candidata")
        self.assertEqual(applicant.partner_id.street_name, "Rua das Flores")
        self.assertEqual(applicant.partner_id.street_number, "100")
        self.assertEqual(applicant.partner_id.district, "Centro")
        self.assertEqual(applicant.partner_id.state_id, self.state)
        self.assertEqual(applicant.partner_id.city_id, self.city)
        self.assertEqual(applicant.bank_account_id.bank_id, self.bank)
        self.assertEqual(applicant.bank_account_id.acc_number, "12345-6")
        self.assertEqual(applicant.bank_account_id.partner_id, applicant.partner_id)
        self.assertEqual(
            sorted(applicant.dependent_ids.mapped("name")), ["Filho Dois", "Filho Um"]
        )

    def test_resubmit_updates_address_and_bank_without_duplicates(self):
        """
        Given an applicant who already submitted address and bank data
        When the form is submitted again with other values
        Then the same address partner and bank account are updated
        """
        address = {"street": "Rua A", "street_number": "1", "zip": "01001-000"}
        bank = {"bank_id": self.bank.id, "bra_number": "0001", "acc_number": "111"}
        self._submit(self.applicant, address=address, bank=bank)
        partner = self.applicant.partner_id
        account = self.applicant.bank_account_id
        address = dict(address, street="Rua B", state_id="sp")
        bank = dict(bank, acc_number="222")
        self.assertTrue(self._submit(self.applicant, address=address, bank=bank))
        self.assertEqual(self.applicant.partner_id, partner)
        self.assertEqual(partner.street_name, "Rua B")
        self.assertEqual(partner.state_id, self.state)
        self.assertEqual(self.applicant.bank_account_id, account)
        self.assertEqual(account.acc_number, "222")
        self.assertEqual(
            self.env["res.partner.bank"].search_count(
                [("partner_id", "=", partner.id)]
            ),
            1,
        )

    def test_resubmit_replaces_dependents(self):
        """
        Given an applicant who already submitted two dependents
        When the form is submitted again with one dependent
        Then only the new dependent remains
        """
        self._submit(
            self.applicant,
            dependents=[
                {"name": "A", "date_of_birth": "2010-01-01"},
                {"name": "B", "date_of_birth": "2012-01-01"},
            ],
        )
        self.assertEqual(len(self.applicant.dependent_ids), 2)
        self._submit(
            self.applicant, dependents=[{"name": "C", "date_of_birth": "2014-01-01"}]
        )
        self.assertEqual(self.applicant.dependent_ids.mapped("name"), ["C"])

    def test_submit_company_form_data(self):
        """
        Given a PJ applicant with a valid token
        When the company form is submitted
        Then legal name, start date and notes are saved
        """
        result = self._submit(
            self.applicant_pj,
            partner_legal_name="Consultoria PJ LTDA",
            start_date="2026-11-01",
            notes="Disponivel em novembro",
        )
        self.assertTrue(result)
        self.assertEqual(self.applicant_pj.partner_legal_name, "Consultoria PJ LTDA")
        self.assertEqual(self.applicant_pj.start_date.isoformat(), "2026-11-01")
        self.assertEqual(self.applicant_pj.notes, "Disponivel em novembro")

    def test_submit_for_unknown_applicant_returns_false(self):
        """
        Given an applicant id that does not exist
        When the form is submitted
        Then the endpoint answers False and nothing is created
        """
        before = self.env["hr.applicant"].search_count([])
        response = self.url_open(
            "/application/999999999/form/submit",
            data=json.dumps(
                {"jsonrpc": "2.0", "method": "call", "params": {"father_name": "x"}}
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertFalse(response.json().get("result"))
        self.assertEqual(self.env["hr.applicant"].search_count([]), before)

    def test_submit_without_valid_token_is_refused(self):
        """
        Given an applicant
        When someone submits data without the token or with a wrong one
        Then nothing is saved (the id alone must not give write access)
        """
        for token in (None, "wrong-token"):
            result = self._submit(self.applicant, token=token, father_name="Intruso")
            self.assertFalse(result)
            self.assertNotEqual(self.applicant.father_name, "Intruso")

    def test_submit_ignores_fields_not_on_the_form(self):
        """
        Given an applicant with a valid token
        When the payload carries fields that are not part of the form
        (stage, salary, token)
        Then they are ignored and the form fields are still saved
        """
        stage = self.env["hr.recruitment.stage"].create({"name": "Contratado test"})
        old_token = self.applicant.access_token
        result = self._submit(
            self.applicant,
            father_name="Pai Legitimo",
            stage_id=stage.id,
            salary_expected=999999.0,
        )
        self.assertTrue(result)
        self.assertEqual(self.applicant.father_name, "Pai Legitimo")
        self.assertNotEqual(self.applicant.stage_id, stage)
        self.assertNotEqual(self.applicant.salary_expected, 999999.0)
        self.assertEqual(self.applicant.access_token, old_token)

    def test_submitted_name_goes_to_the_candidate_name(self):
        """
        Given a CLT applicant with a valid token
        When the form is submitted with the person's name
        Then it becomes the candidate name of the application
        """
        self.assertTrue(self._submit(self.applicant, name="Maria Candidata Silva"))
        self.assertEqual(self.applicant.partner_name, "Maria Candidata Silva")
