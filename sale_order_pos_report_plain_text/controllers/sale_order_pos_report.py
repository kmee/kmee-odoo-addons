from odoo import http
from odoo.http import request


class SaleOrderPosController(http.Controller):
    @http.route(
        "/sale_order_pos_report_plain_text/<int:sale_order_id>",
        type="http",
        auth="user",
    )
    def store_ticket_report(self, sale_order_id, **post):
        sale_order = request.env["sale.order"].browse(sale_order_id)
        if not sale_order.exists():
            return request.not_found()

        pdf = request.env.ref(
            "sale_order_pos_report_plain_text.action_report_saleorder_compact"
        )._render_qweb_pdf(sale_order.ids)[0]
        response = request.make_response(pdf)
        response.headers["Content-Type"] = "application/pdf;"
        response.headers[
            "Content-Disposition"
        ] = f'inline; filename="sale_order_{sale_order_id}.pdf"'
        return response
