from unittest.mock import patch

from odoo import SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

from odoo.addons.queue_job.tests.common import trap_jobs


class TestHelpdeskReprocessWizard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, test_queue_job_no_delay=True))
        cls.team = cls.env["helpdesk.ticket.team"].create(
            {
                "name": "Reprocess Wizard Team",
                "alias_name": "reprocess-wizard-team",
            }
        )

    def test_action_start_reprocess_enqueues_queue_job(self):
        legacy_html = "<p>" + ("y" * 2500) + "</p>"
        ticket = self.env["helpdesk.ticket"].create(
            {
                "name": "Legacy queue ticket",
                "description": legacy_html,
                "description_full": False,
                "team_id": self.team.id,
            }
        )
        wizard = self.env["helpdesk.ticket.reprocess.wizard"].create({})

        with patch.object(type(wizard), "_is_jobrunner_enabled", return_value=True):
            with trap_jobs() as trap:
                with self.assertRaises(UserError):
                    wizard.action_start_reprocess()
                trap.assert_jobs_count(1)
                self.assertEqual(
                    trap.enqueued_jobs[0].method_name,
                    "_queue_job_smoke_test",
                )
                trap.perform_enqueued_jobs()

            with trap_jobs() as trap:
                wizard.action_start_reprocess()
                trap.assert_jobs_count(1)
                self.assertEqual(
                    trap.enqueued_jobs[0].method_name,
                    "reprocess_description_queue_job",
                )
                trap.perform_enqueued_jobs()

        wizard.invalidate_recordset()
        ticket.invalidate_recordset()

        self.assertEqual(wizard.state, "done")
        self.assertGreaterEqual(wizard.updated_count, 1)
        self.assertTrue(ticket.description_full)
        self.assertTrue(ticket.has_description_full)

    def test_action_start_reprocess_runs_from_system_user(self):
        legacy_html = "<p>" + ("w" * 2500) + "</p>"
        ticket = self.env["helpdesk.ticket"].create(
            {
                "name": "Legacy system queue ticket",
                "description": legacy_html,
                "description_full": False,
                "team_id": self.team.id,
            }
        )
        wizard = self.env["helpdesk.ticket.reprocess.wizard"].create({})

        with patch.object(type(wizard), "_is_jobrunner_enabled", return_value=True):
            with trap_jobs() as trap:
                with self.assertRaises(UserError):
                    wizard.with_user(SUPERUSER_ID).action_start_reprocess()
                trap.assert_jobs_count(1)
                self.assertEqual(
                    trap.enqueued_jobs[0].method_name,
                    "_queue_job_smoke_test",
                )
                trap.assert_jobs_count(1)
                trap.perform_enqueued_jobs()

            with trap_jobs() as trap:
                wizard.with_user(SUPERUSER_ID).action_start_reprocess()
                trap.assert_jobs_count(1)
                self.assertEqual(
                    trap.enqueued_jobs[0].method_name,
                    "reprocess_description_queue_job",
                )
                trap.perform_enqueued_jobs()

        wizard.invalidate_recordset()
        ticket.invalidate_recordset()

        self.assertEqual(wizard.state, "done")
        self.assertGreaterEqual(wizard.updated_count, 1)
        self.assertTrue(ticket.description_full)
        self.assertTrue(ticket.has_description_full)

    def test_action_start_reprocess_raises_without_jobrunner(self):
        legacy_html = "<p>" + ("z" * 2500) + "</p>"
        ticket = self.env["helpdesk.ticket"].create(
            {
                "name": "Legacy sync ticket",
                "description": legacy_html,
                "description_full": False,
                "team_id": self.team.id,
            }
        )
        wizard = self.env["helpdesk.ticket.reprocess.wizard"].create({})

        with patch.object(type(wizard), "_is_jobrunner_enabled", return_value=False):
            with self.assertRaises(UserError):
                wizard.action_start_reprocess()

        wizard.invalidate_recordset()
        ticket.invalidate_recordset()

        self.assertEqual(wizard.state, "draft")
        self.assertEqual(wizard.updated_count, 0)
        self.assertFalse(wizard.log_text)
        self.assertTrue(ticket.description_full)
        self.assertTrue(ticket.has_description_full)

    def test_action_validate_queue_job_marks_wizard_as_validated(self):
        wizard = self.env["helpdesk.ticket.reprocess.wizard"].create({})

        with patch.object(type(wizard), "_is_jobrunner_enabled", return_value=True):
            with trap_jobs() as trap:
                wizard.action_validate_queue_job()
                trap.assert_jobs_count(1)
                self.assertEqual(
                    trap.enqueued_jobs[0].method_name,
                    "_queue_job_smoke_test",
                )
                trap.perform_enqueued_jobs()

        wizard.invalidate_recordset()
        self.assertEqual(wizard.validation_state, "success")
        self.assertIn("queue_job", wizard.validation_message)
