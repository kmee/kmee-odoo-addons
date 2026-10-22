# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestDescriptionOptimizerTour(HttpCase):
    def test_read_more_widget(self):
        team = self.env["helpdesk.ticket.team"].create({"name": "Tour Team"})
        description = (
            "<div>"
            + "".join("<p>Linha %d de conteudo.</p>" % i for i in range(120))
            + "</div>"
        )
        ticket = self.env["helpdesk.ticket"].create(
            {"name": "Tour Ticket", "description": description, "team_id": team.id}
        )
        self.assertTrue(ticket.has_description_full)
        self.start_tour(
            f"/web#model=helpdesk.ticket&id={ticket.id}&view_type=form",
            "helpdesk_mgmt_description_optimizer_tour",
            login="admin",
        )
