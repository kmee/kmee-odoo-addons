# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCrmWip(TransactionCase):
    def test_lead_state_follows_stage(self):
        stage = self.env["crm.stage"].create({"name": "WIP stage", "state": "open"})
        lead = self.env["crm.lead"].create({"name": "WIP lead", "stage_id": stage.id})
        self.assertEqual(lead.state, "open")
        stage.state = "done"
        self.assertEqual(lead.state, "done")
