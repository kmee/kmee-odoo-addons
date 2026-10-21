# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase, tagged

MARKER = "DescricaoUnicaDaVagaXYZ"


@tagged("post_install", "-at_install")
class TestDisplayDescription(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.job = cls.env["hr.job"].create(
            {
                "name": "Vaga com descricao",
                "description": MARKER,
                "is_published": True,
                "address_id": cls.env.company.partner_id.id,
            }
        )

    def _page(self):
        response = self.url_open("/jobs/detail/%d" % self.job.id)
        self.assertEqual(response.status_code, 200)
        return response.text

    def test_default_is_to_display(self):
        """
        Dado uma vaga nova
        Quando nada e informado
        Entao website_display_description e verdadeiro
        """
        self.assertTrue(self.job.website_display_description)

    def test_page_shows_description_by_default(self):
        """
        Dado uma vaga publicada com descricao e o flag ligado
        Quando o visitante abre a pagina da vaga
        Entao a descricao aparece
        """
        self.assertIn(MARKER, self._page())

    def test_page_hides_description_when_flag_is_off(self):
        """
        Dado uma vaga publicada com descricao e o flag desligado
        Quando o visitante abre a pagina da vaga
        Entao a descricao NAO aparece
        """
        self.job.website_display_description = False
        self.assertNotIn(MARKER, self._page())

    def test_flag_toggle_round_trip(self):
        """
        Dado uma vaga com o flag desligado
        Quando ele e religado
        Entao a descricao volta a aparecer na pagina
        """
        self.job.website_display_description = False
        self.assertNotIn(MARKER, self._page())
        self.job.website_display_description = True
        self.assertIn(MARKER, self._page())

    def test_job_form_view_shows_flag_before_description(self):
        """
        Dado o formulario da vaga
        Quando a view e montada
        Entao o campo website_display_description aparece antes da descricao
        """
        arch = self.env["hr.job"].get_view(
            self.env.ref("hr.view_hr_job_form").id, "form"
        )["arch"]
        self.assertIn("website_display_description", arch)
        self.assertLess(
            arch.index('name="website_display_description"'),
            arch.index('name="description"'),
        )

    def test_website_template_hides_description_when_disabled(self):
        view = self.env.ref(
            "website_hr_recruitment_display_description.default_website_description"
        )
        self.assertIn("job.website_display_description", view.arch_db)
