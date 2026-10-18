# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDisplayDescription(TransactionCase):
    def test_default_and_form_view(self):
        job = self.env["hr.job"].create({"name": "Developer"})
        self.assertTrue(job.website_display_description)
        job.website_display_description = False
        self.assertFalse(job.website_display_description)
        arch = self.env["hr.job"].get_view(
            self.env.ref("hr.view_hr_job_form").id, "form"
        )["arch"]
        self.assertIn("website_display_description", arch)
