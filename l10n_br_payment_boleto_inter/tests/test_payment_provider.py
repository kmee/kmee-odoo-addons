# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import BancoInterCommon, ResponseStub


@tagged("post_install", "-at_install")
class TestInterProvider(BancoInterCommon):
    def test_incomplete_configuration_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["payment.provider"].create(
                {"name": "Inter sem credenciais", "code": "inter", "state": "test"}
            )

    def test_disabled_provider_can_be_incomplete(self):
        provider = self.env["payment.provider"].create(
            {"name": "Inter desligado", "code": "inter", "state": "disabled"}
        )
        self.assertEqual(provider.state, "disabled")

    def test_default_payment_method_is_boleto(self):
        self.assertEqual(self.provider._get_default_payment_method_codes(), {"boleto"})
        other = self.env["payment.provider"].search([("code", "!=", "inter")], limit=1)
        if other:
            self.assertNotEqual(other._get_default_payment_method_codes(), {"boleto"})

    def test_only_brl_is_supported(self):
        currencies = self.provider._get_supported_currencies()
        self.assertEqual(currencies.mapped("name"), ["BRL"])

    @mute_logger("odoo.addons.l10n_br_payment_boleto_inter.models.banco_inter_mixin")
    def test_pdf_with_corrupted_base64(self):
        response = ResponseStub(json_data={"pdf": "not base64 !!"})
        with self.assertRaises(UserError):
            self.mixin._inter_extract_pdf(response)

    def test_pdf_json_without_pdf_content_header(self):
        """Base64 válido que não é PDF ainda é devolvido, só com aviso no log."""
        response = ResponseStub(json_data={"pdf": "aGVsbG8="})
        with self.assertLogs(
            "odoo.addons.l10n_br_payment_boleto_inter.models.banco_inter_mixin",
            level="WARNING",
        ):
            self.assertEqual(self.mixin._inter_extract_pdf(response), "aGVsbG8=")
