# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest import SkipTest

from brbank import StatusCanonico, registro

from odoo.tests.common import TransactionCase

from ..utils import config as brbank_config
from .fake_bank import BANK, FakeAdapter, FakeBasicAdapter, reset_bank

FAKE = "brbank_test_fake"
FAKE_BASIC = "brbank_test_fake_basic"
DUMMY_BY_TYPE = {bool: False, int: 1, float: 1.0, str: "1234567", bytes: b"x"}
# Dummy values the validation of the library accepts, where the type is not
# enough: by key, then by adapter.
DUMMY_BY_KEY = {
    "agencia": "1234",
    "cnpj_empresa": "11222333000181",
    "digito_conta": "1",
    "documento_beneficiario": "11222333000181",
}
DUMMY_BY_ADAPTER = {
    "banrisul": {"codigo_beneficiario": "1234567890123", "especie": "02"},
    "safra": {"especie": "01"},
    "santander": {"tipo_chave_pix": "EVP"},
}
# A random Pix key (EVP): the C6 refuses any other kind.
PIX_KEY = "123e4567-e89b-42d3-a456-426614174000"


def register_fake_adapters(test_class):
    registro.registrar_adapter(FAKE, FakeAdapter)
    registro.registrar_adapter(FAKE_BASIC, FakeBasicAdapter)

    def unregister():
        registro._manuais.pop(FAKE, None)
        registro._manuais.pop(FAKE_BASIC, None)

    test_class.addClassCleanup(unregister)


class BrbankCommon:
    """Fixtures shared by the TransactionCase and HttpCase suites."""

    @classmethod
    def _setup_brbank(cls):
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                tracking_disable=True,
                test_queue_job_no_delay=True,
                lang="en_US",
            )
        )
        company = cls.env.company
        if not company.chart_template_id:
            raise SkipTest("The test company needs a chart of accounts.")
        register_fake_adapters(cls)
        reset_bank()
        cls.bank = BANK
        cls.provider = cls._create_provider(FAKE)
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", company.id)], limit=1
        )
        cls.payment_mode = cls.env["account.payment.mode"].create(
            {
                "name": "Boleto brbank",
                "bank_account_link": "fixed",
                "fixed_journal_id": cls.bank_journal.id,
                "payment_method_id": cls.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
                "generate_boletos_on_invoice": True,
                "payment_provider_id": cls.provider.id,
                "payment_boleto_penalty": 0.02,
                "payment_boleto_interest": 0.01,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Cliente Boleto",
                "is_company": True,
                "legal_name": "Cliente Boleto Ltda",
                "cnpj_cpf": "11.222.333/0001-81",
                "street_name": "Rua dos Testes",
                "street_number": "100",
                "district": "Centro",
                "zip": "30140-071",
                "city": "Belo Horizonte",
                "state_id": cls.env.ref("base.state_br_mg").id,
                "country_id": cls.env.ref("base.br").id,
                "email": "financeiro@example.com",
            }
        )
        cls.payment_term = cls.env["account.payment.term"].create(
            {
                "name": "30/60/90",
                "line_ids": [
                    (0, 0, {"value": "percent", "value_amount": 30.0, "days": 30}),
                    (0, 0, {"value": "percent", "value_amount": 30.0, "days": 60}),
                    (0, 0, {"value": "balance", "value_amount": 0.0, "days": 90}),
                ],
            }
        )

    @classmethod
    def _create_provider(cls, adapter, **values):
        return cls.env["payment.provider"].create(
            dict(
                {
                    "name": f"Banco de teste {adapter}",
                    "code": "brbank",
                    "brbank_adapter": adapter,
                    "state": "test",
                    "company_id": cls.env.company.id,
                    "brbank_client_id": "client-id",
                    "brbank_client_secret": "client-secret",
                    "brbank_extra_config": json.dumps({"numero_cliente": 42}),
                },
                **values,
            )
        )

    @classmethod
    def _fill_for_test(cls, provider):
        """Dummy credentials and settings typed after the adapter config."""
        provider.action_brbank_fill_settings_template()
        config_cls = brbank_config.config_class(
            registro.obter_classe(provider.brbank_adapter)
        )
        public = json.loads(provider.brbank_extra_config)
        secret = json.loads(provider.brbank_secret_config)
        overrides = DUMMY_BY_ADAPTER.get(provider.brbank_adapter, {})
        for key in brbank_config.describe(config_cls):
            target = secret if key["secret"] else public
            name = key["name"]
            if name in overrides:
                target[name] = overrides[name]
            elif key["required"] and not key["generic"]:
                target[name] = DUMMY_BY_KEY.get(
                    name, DUMMY_BY_TYPE.get(key["type"], "1234567")
                )
        provider.write(
            {
                "brbank_client_id": "client-id",
                "brbank_client_secret": "client-secret",
                "brbank_username": "usuario",
                # The PinBank password is also its AES key: 16 bytes.
                "brbank_password": "0123456789abcdef",
                "brbank_pix_key": PIX_KEY,
                "brbank_refresh_token": "refresh-token",
                "brbank_extra_config": json.dumps(public),
                "brbank_secret_config": json.dumps(secret),
                "state": "enabled",
            }
        )

    def _create_invoice(self, amount=1000.0, post=True):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": "2026-01-05",
                "invoice_payment_term_id": self.payment_term.id,
                "payment_mode_id": self.payment_mode.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Servico",
                            "quantity": 1,
                            "price_unit": amount,
                            "tax_ids": [(6, 0, [])],
                        },
                    )
                ],
            }
        )
        if post:
            invoice.action_post()
        return invoice

    def _brbank_txs(self, invoice):
        return invoice.transaction_ids.filtered(
            lambda t: t.provider_code == "brbank"
        ).sorted(lambda t: (t.due_date, t.id))

    def _bank_title(self, transaction):
        return self.bank["titles"][transaction.provider_reference]

    def _set_bank_status(self, transaction, status, paid=None):
        title = self._bank_title(transaction)
        title["status"] = StatusCanonico(status)
        if paid is not None:
            title["valor_pago"] = paid


class BrbankTransactionCase(BrbankCommon, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_brbank()

    def setUp(self):
        super().setUp()
        reset_bank()
