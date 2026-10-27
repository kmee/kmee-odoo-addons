from unittest.mock import patch

from odoo.tests.common import TransactionCase

MAKE_REQUEST = (
    "odoo.addons.l10n_br_payment_pinbank.models.payment_provider."
    "Paymentprovider._boleto_pinbank_make_request"
)


def boleto_response(our_number, status=None):
    data = {
        "NossoNumero": our_number,
        "LinhaDigitavel": "12345.67890 12345.678901 12345.678901 1 23456789012345",
        "CodigoBarras": "12345678901234567890123456789012345678901234",
    }
    if status:
        data["Status"] = status
    return {"Data": data}


def patch_make_request(**kwargs):
    return patch(MAKE_REQUEST, **kwargs)


class PinbankCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.provider = cls.env.ref(
            "l10n_br_payment_pinbank.payment_acquirer_boleto_pinbank"
        )
        cls.provider.write(
            {
                "pinbank_user": "abcd1234",
                "pinbank_secret": "secret",
                "pinbank_channel": 10,
                "pinbank_client": 1000,
                "pinbank_request_origin": "1",
                "state": "test",
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Cliente Boleto",
                "legal_name": "Cliente Boleto LTDA",
                "email": "cliente@example.com",
                "cnpj_cpf": "73.145.637/0001-40",
                "zip": "08473-002",
            }
        )

    @classmethod
    def _create_tx(cls, **vals):
        return cls.env["payment.transaction"].create(
            {
                "reference": "INV/2026/00001/1",
                "amount": 100.0,
                "due_date": "2026-02-05",
                "currency_id": cls.env.ref("base.BRL").id,
                "partner_id": cls.partner.id,
                "provider_id": cls.provider.id,
                "is_boleto_payment": True,
                **vals,
            }
        )
