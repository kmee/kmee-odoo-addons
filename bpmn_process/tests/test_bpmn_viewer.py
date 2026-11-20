# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import HttpCase, tagged

from .common import sample_xml


@tagged("post_install", "-at_install")
class TestBpmnViewerTour(HttpCase):
    def test_viewer_tour(self):
        result = self.env["bpmn.process"].import_xml("sample_tour", sample_xml())
        self.env["bpmn.element.test"].record_results(
            [
                {
                    "bpmn_id": "Task_Sample_Invoice",
                    "process": "sample_tour",
                    "scenario": "invoice e2e",
                    "result": "failed",
                }
            ]
        )
        self.start_tour(
            "/odoo/action-bpmn_process.bpmn_process_action/%s" % result["process_id"],
            "bpmn_process_viewer_tour",
            login="admin",
            timeout=300,
        )
        process = self.env["bpmn.process"].browse(result["process_id"])
        quote = process.element_ids.filtered(lambda e: e.bpmn_id == "Task_Sample_Quote")
        self.assertIn(
            "Comment from the tour", "".join(quote.message_ids.mapped("body"))
        )
        self.assertFalse(process.lock_user_id)
