import base64

from odoo import http
from odoo.http import request


class PaymentController(http.Controller):
    @http.route(
        "/payment/boleto/<int:transaction_id>", type="http", auth="public", website=True
    )
    def boleto_page(self, transaction_id, download=False, **kwargs):
        tx = (
            request.env["payment.transaction"]
            .sudo()
            .search([("id", "=", transaction_id)], limit=1)
        )
        if not tx or not tx.boleto_pdf:
            return request.render("website.404")

        pdf_content = base64.b64decode(tx.boleto_pdf)
        disposition = "attachment" if download else "inline"

        return request.make_response(
            pdf_content,
            headers=[
                ("Content-Type", "application/pdf"),
                (
                    "Content-Disposition",
                    f'{disposition}; filename="boleto_{tx.reference}.pdf"',
                ),
            ],
        )
