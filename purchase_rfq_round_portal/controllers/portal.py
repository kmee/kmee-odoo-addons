# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class RfqRoundPortal(CustomerPortal):
    @http.route(
        ["/my/purchase/<int:order_id>/rfq_response"],
        type="http",
        auth="public",
        website=True,
        methods=["GET", "POST"],
    )
    def portal_rfq_round_response(self, order_id, access_token=None, **post):
        """Página em que o fornecedor responde a cotação de uma rodada."""
        try:
            order_sudo = self._document_check_access(
                "purchase.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")
        if not order_sudo.rfq_round_id:
            return request.redirect(order_sudo.get_portal_url())
        errors = {}
        submitted = False
        if request.httprequest.method == "POST":
            errors = order_sudo._rfq_portal_submit(post)
            submitted = not errors
        values = {
            "order": order_sudo,
            "rfq_round": order_sudo.rfq_round_id,
            "lines": order_sudo._rfq_portal_lines(),
            "line_fields": order_sudo._rfq_portal_line_fields(),
            "rfq_can_answer": order_sudo._rfq_portal_can_answer(),
            "errors": errors,
            "post": post if errors else {},
            "submitted": submitted,
            "access_token": access_token,
            "page_name": "purchase",
        }
        return request.render(
            "purchase_rfq_round_portal.portal_rfq_round_response", values
        )
