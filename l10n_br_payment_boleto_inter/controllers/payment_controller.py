import base64

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils


class PaymentController(http.Controller):
    @http.route(
        "/payment/boleto/<int:transaction_id>", type="http", auth="public", website=True
    )
    def boleto_page(self, transaction_id, access_token=None, download=False, **kwargs):
        """Devolve o PDF do boleto da transação.

        O boleto traz nome, documento, endereço e valor do pagador, então a rota
        exige o token de acesso da transação para quem não estiver autenticado
        com direito sobre ela.

        :param int transaction_id: A transação dona do boleto.
        :param str access_token: O token que autoriza o acesso ao boleto.
        :param download: Baixa o arquivo em vez de exibi-lo.
        """
        tx_sudo = (
            request.env["payment.transaction"].sudo().browse(transaction_id).exists()
        )
        if not tx_sudo or not tx_sudo.boleto_pdf:
            return request.render("website.404")

        if not self._boleto_check_access(tx_sudo, access_token):
            raise AccessError(_("Você não tem acesso a este boleto."))

        pdf_content = base64.b64decode(tx_sudo.boleto_pdf)
        disposition = "attachment" if download else "inline"
        filename = f'filename="boleto_{tx_sudo.reference}.pdf"'

        return request.make_response(
            pdf_content,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Disposition", disposition + "; " + filename),
            ],
        )

    @staticmethod
    def _boleto_check_access(tx_sudo, access_token):
        """Diz se o visitante pode ver o boleto da transação.

        :param tx_sudo: A transação, em sudo.
        :param str access_token: O token recebido na URL.
        :return: Se o acesso é permitido.
        :rtype: bool
        """
        if access_token and payment_utils.check_access_token(
            access_token, tx_sudo.reference, tx_sudo.partner_id.id
        ):
            return True
        # Um usuário interno, ou o próprio cliente autenticado, dispensa o token.
        if request.env.user._is_internal():
            return True
        partner = request.env.user.partner_id
        return bool(
            partner
            and tx_sudo.partner_id
            and tx_sudo.partner_id.commercial_partner_id
            == partner.commercial_partner_id
        )
