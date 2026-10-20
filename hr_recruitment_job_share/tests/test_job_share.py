# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestJobShare(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.base_url_param = (
            cls.env["ir.config_parameter"].sudo().get_param("web.base.url")
        )
        cls.job = cls.env["hr.job"].create(
            {
                "name": "Vaga Compartilhada XPTO",
                "address_id": cls.env.company.partner_id.id,
            }
        )

    # ------------------------------------------------------------------
    # modelo
    # ------------------------------------------------------------------
    def test_create_generates_token(self):
        """
        Dado uma vaga nova
        Quando ela e criada sem token
        Entao um token de acesso e gerado e ela nao nasce compartilhada
        """
        self.assertTrue(self.job.access_token)
        self.assertFalse(self.job.is_shared)

    def test_create_multi_generates_distinct_tokens(self):
        """
        Dado duas vagas criadas em lote
        Quando o lote e criado
        Entao cada uma recebe um token proprio
        """
        jobs = self.env["hr.job"].create([{"name": "Job A"}, {"name": "Job B"}])
        self.assertTrue(all(jobs.mapped("access_token")))
        self.assertNotEqual(jobs[0].access_token, jobs[1].access_token)

    def test_create_keeps_given_token(self):
        """
        Dado um token informado na criacao
        Quando a vaga e criada
        Entao o token informado e mantido
        """
        job = self.env["hr.job"].create({"name": "Job C", "access_token": "fixed"})
        self.assertEqual(job.access_token, "fixed")

    def test_copy_does_not_copy_token(self):
        """
        Dado uma vaga com token
        Quando ela e duplicada
        Entao a copia recebe outro token (o link original nao abre a copia)
        """
        copy = self.job.copy()
        self.assertTrue(copy.access_token)
        self.assertNotEqual(copy.access_token, self.job.access_token)

    def test_share_url_uses_base_url_id_and_token(self):
        """
        Dado uma vaga
        Quando a URL de compartilhamento e montada
        Entao ela e base_url/jobs/details/<id>?access_token=<token>
        """
        expected = "%s/jobs/details/%d?access_token=%s" % (
            self.base_url_param,
            self.job.id,
            self.job.access_token,
        )
        self.assertEqual(self.job.get_share_url(), expected)
        self.assertEqual(self.job.application_url, expected)

    def test_application_url_empty_without_token(self):
        """
        Dado uma vaga sem token de acesso
        Quando a URL da vaga e calculada
        Entao ela fica vazia
        """
        self.job.access_token = False
        self.assertEqual(self.job.application_url, "")

    def test_share_job_opens_wizard_rotates_token_and_marks_shared(self):
        """
        Dado uma vaga nao compartilhada
        Quando o botao Compartilhar Vaga e acionado
        Entao abre o wizard, marca como compartilhada e troca o token
        """
        old_token = self.job.access_token
        action = self.job.action_share_job()
        self.assertEqual(action["res_model"], "job.share.wizard")
        self.assertEqual(action["context"]["default_job_id"], self.job.id)
        self.assertTrue(self.job.is_shared)
        self.assertNotEqual(self.job.access_token, old_token)

    def test_wizard_shows_the_job_url(self):
        """
        Dado o wizard de compartilhamento aberto para a vaga
        Quando ele e criado
        Entao a URL exibida e a URL de compartilhamento da vaga
        """
        self.job.action_share_job()
        wizard = self.env["job.share.wizard"].create({"job_id": self.job.id})
        self.assertEqual(wizard.application_url, self.job.get_share_url())

    def test_marking_shared_rotates_token(self):
        """
        Dado uma vaga
        Quando is_shared passa a verdadeiro na gravacao
        Entao o token e renovado; gravar outro campo nao renova
        """
        token = self.job.access_token
        self.job.write({"description": "outra coisa"})
        self.assertEqual(self.job.access_token, token)
        self.job.write({"is_shared": True})
        self.assertNotEqual(self.job.access_token, token)

    def test_wizard_form_view_has_copy_widget(self):
        """
        Dado o formulario do wizard
        Quando a view e montada
        Entao exibe application_url
        """
        arch = self.env["job.share.wizard"].get_view(
            self.env.ref("hr_recruitment_job_share.job_share_wizard_form_view").id,
            "form",
        )["arch"]
        self.assertIn("application_url", arch)

    def test_job_form_has_share_button(self):
        """
        Dado o formulario da vaga
        Quando a view e montada
        Entao existe o botao action_share_job
        """
        arch = self.env["hr.job"].get_view(
            self.env.ref("hr_recruitment.hr_job_survey").id, "form"
        )["arch"]
        self.assertIn("action_share_job", arch)

    # ------------------------------------------------------------------
    # controller
    # ------------------------------------------------------------------
    def _details(self, job, token=None):
        url = "/jobs/details/%d" % job.id
        if token is not None:
            url += "?access_token=%s" % token
        return self.url_open(url)

    def test_details_with_valid_token_shows_unpublished_job(self):
        """
        Dado uma vaga NAO publicada no site
        Quando um visitante abre o link com o token correto
        Entao a pagina da vaga abre (200) com o titulo da vaga
        """
        self.assertFalse(self.job.is_published)
        response = self._details(self.job, self.job.access_token)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Vaga Compartilhada XPTO", response.text)

    def test_details_apply_button_carries_token_for_unpublished_job(self):
        """
        Dado uma vaga nao publicada aberta pelo link compartilhado
        Quando a pagina e renderizada
        Entao o botao Apply Now leva o token na URL de candidatura
        """
        response = self._details(self.job, self.job.access_token)
        self.assertIn(
            "/jobs/apply/%d?access_token=%s" % (self.job.id, self.job.access_token),
            response.text,
        )

    def test_details_apply_button_has_no_token_for_published_job(self):
        """
        Dado uma vaga publicada aberta pelo link compartilhado
        Quando a pagina e renderizada
        Entao o botao Apply Now usa a URL publica, sem token
        """
        self.job.is_published = True
        response = self._details(self.job, self.job.access_token)
        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/jobs/apply/%d"' % self.job.id, response.text)
        self.assertNotIn("access_token=%s" % self.job.access_token, response.text)

    def test_details_with_wrong_token_is_not_found(self):
        """
        Dado uma vaga com token
        Quando o visitante usa um token errado
        Entao a resposta e 404
        """
        self.assertEqual(self._details(self.job, "errado").status_code, 404)

    def test_details_without_token_is_not_found(self):
        """
        Dado uma vaga com token
        Quando o visitante abre o link sem token
        Entao a resposta e 404
        """
        self.assertEqual(self._details(self.job).status_code, 404)

    def test_details_old_token_stops_working_after_new_share(self):
        """
        Dado um link compartilhado
        Quando a vaga e compartilhada de novo (token rotacionado)
        Entao o link antigo para de funcionar e o novo funciona
        """
        old_token = self.job.access_token
        self.job.action_share_job()
        self.assertEqual(self._details(self.job, old_token).status_code, 404)
        self.assertEqual(
            self._details(self.job, self.job.access_token).status_code, 200
        )

    def test_details_unknown_job_is_not_found(self):
        """
        Dado um id de vaga inexistente
        Quando o visitante abre o link
        Entao a resposta e 404
        """
        response = self.url_open("/jobs/details/99999999?access_token=abc")
        self.assertEqual(response.status_code, 404)

    def test_apply_with_token_opens_form_of_unpublished_job(self):
        """
        Dado uma vaga nao publicada
        Quando o visitante abre a candidatura com o token correto
        Entao o formulario de candidatura abre (200)
        """
        response = self.url_open(
            "/jobs/apply/%d?access_token=%s" % (self.job.id, self.job.access_token)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Vaga Compartilhada XPTO", response.text)

    def test_apply_unpublished_without_token_is_not_found(self):
        """
        Dado uma vaga nao publicada
        Quando o visitante abre a candidatura sem token
        Entao a resposta e 404
        """
        response = self.url_open("/jobs/apply/%d" % self.job.id)
        self.assertEqual(response.status_code, 404)

    def test_apply_published_without_token_opens_form(self):
        """
        Dado uma vaga publicada
        Quando o visitante abre a candidatura sem token
        Entao o formulario abre (200)
        """
        self.job.is_published = True
        response = self.url_open("/jobs/apply/%d" % self.job.id)
        self.assertEqual(response.status_code, 200)

    def test_apply_unknown_job_is_not_found(self):
        """
        Dado um id de vaga inexistente
        Quando o visitante abre a candidatura
        Entao a resposta e 404
        """
        response = self.url_open("/jobs/apply/99999999?access_token=abc")
        self.assertEqual(response.status_code, 404)
