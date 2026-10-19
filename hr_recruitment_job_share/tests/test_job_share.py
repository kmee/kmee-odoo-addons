# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestJobShare(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

    def test_create_multi_generates_distinct_tokens(self):
        jobs = self.env["hr.job"].create([{"name": "Job A"}, {"name": "Job B"}])
        self.assertTrue(all(jobs.mapped("access_token")))
        self.assertNotEqual(jobs[0].access_token, jobs[1].access_token)

    def test_create_keeps_given_token(self):
        job = self.env["hr.job"].create({"name": "Job C", "access_token": "fixed"})
        self.assertEqual(job.access_token, "fixed")

    def test_share_job_opens_wizard_and_marks_shared(self):
        job = self.env["hr.job"].create({"name": "Job D"})
        old_token = job.access_token
        action = job.action_share_job()
        self.assertEqual(action["res_model"], "job.share.wizard")
        self.assertTrue(job.is_shared)
        self.assertNotEqual(job.access_token, old_token)
        self.assertIn(job.access_token, job.get_share_url())
        self.assertEqual(job.application_url, job.get_share_url())
