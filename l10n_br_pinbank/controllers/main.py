# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


_logger = logging.getLogger(__name__)


class PinBankController(http.Controller):
    _return_url = '/payment/pinbank/return'

    @http.route(
        _return_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False,
        save_session=False
    )
    def pinbank_return_from_checkout(self, reference, **data):
        """ Process the notification data sent by PinBank after redirection from checkout.

        :param str reference: The transaction reference embedded in the return URL.
        :param dict data: The notification data.
        """
        _logger.info("Handling redirection from Pinbank with data:\n%s", pprint.pformat(data))
        tx_sudo._handle_notification_data('pinbank', data)
        return request.redirect('/payment/status')

