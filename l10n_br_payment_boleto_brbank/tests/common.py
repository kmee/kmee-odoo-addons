# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest import SkipTest

from brbank import StatusCanonico, registro

from odoo.tests.common import TransactionCase

from .fake_bank import BANK, FakeAdapter, FakeBasicAdapter, reset_bank

FAKE = "brbank_test_fake"
FAKE_BASIC = "brbank_test_fake_basic"


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
