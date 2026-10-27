# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""The credentials of a provider become a bank connection (16.0.2.0.0).

A fresh database has no old columns, so the test adds them in its own
transaction (undone at the end), fills them as the old version would have and
runs the function of the migration over that data.
"""

import base64
import importlib.util
import json
import os

from odoo.tests import tagged

from .common import FAKE, BrbankTransactionCase

MIGRATION = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    "migrations",
    "16.0.2.0.0",
    "post-migration.py",
)
OLD_COLUMNS = {
    "brbank_client_id": "varchar",
    "brbank_client_secret": "varchar",
    "brbank_username": "varchar",
    "brbank_password": "varchar",
    "brbank_pix_key": "varchar",
    "brbank_refresh_token": "varchar",
    "brbank_extra_config": "text",
    "brbank_secret_config": "text",
    "brbank_webhook_token": "varchar",
    "brbank_certificate": "bytea",
    "brbank_private_key": "bytea",
}


def load_migration():
    spec = importlib.util.spec_from_file_location("brbank_post_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("post_install", "-at_install")
class TestProviderToConnection(BrbankTransactionCase):
    def setUp(self):
        super().setUp()
        self.migration = load_migration()
        for column, kind in OLD_COLUMNS.items():
            self.env.cr.execute(
                f"ALTER TABLE payment_provider ADD COLUMN IF NOT EXISTS {column} {kind}"
            )
        # Events are born with a connection now: the old rows had none yet.
        self.env.cr.execute(
            "ALTER TABLE l10n_br_brbank_event ALTER COLUMN connection_id DROP NOT NULL"
        )

    def _old_provider(self, name, state, **columns):
        provider = self.env["payment.provider"].create(
            {
                "name": name,
                "code": "brbank",
                "brbank_adapter": FAKE,
                "state": "disabled",
                "company_id": self.env.company.id,
            }
        )
        assignments = ", ".join(["state = %s"] + [f"{c} = %s" for c in columns])
        self.env.cr.execute(
            f"UPDATE payment_provider SET {assignments} WHERE id = %s",  # noqa: S608
            [state, *columns.values(), provider.id],
        )
        provider.invalidate_recordset()
        return provider

    def _old_event(self, provider, reference):
        self.env.cr.execute(
            "INSERT INTO l10n_br_brbank_event "
            "(provider_id, bank, reference, event_type, state, attempts) "
            "VALUES (%s, 'fake', %s, 'LIQUIDADO', 'done', 0) RETURNING id",
            (provider.id, reference),
        )
        return self.env["l10n_br.brbank.event"].browse(self.env.cr.fetchone()[0])

    def test_provider_becomes_connection(self):
        provider = self._old_provider(
            "Old provider",
            "test",
            brbank_client_id="old-id",
            brbank_client_secret="old-secret",
            brbank_refresh_token="old-refresh",
            brbank_extra_config=json.dumps({"numero_cliente": 9}),
            brbank_webhook_token="old-webhook-token",
            brbank_certificate=b"cert-pem",
        )
        event = self._old_event(provider, "B1")
        created = self.migration.migrate_providers(self.env.cr)
        self.env.invalidate_all()
        connection = provider.brbank_connection_id
        self.assertEqual(created, [connection.id])
        self.assertEqual(connection.name, "Old provider")
        self.assertEqual(connection.adapter, FAKE)
        self.assertEqual(connection.environment, "test")
        self.assertEqual(connection.client_id, "old-id")
        self.assertEqual(connection.client_secret, "old-secret")
        self.assertEqual(connection.refresh_token, "old-refresh")
        self.assertEqual(json.loads(connection.extra_config), {"numero_cliente": 9})
        self.assertEqual(base64.b64decode(connection.certificate), b"cert-pem")
        # The URL registered at the bank keeps its token.
        self.assertEqual(connection.webhook_token, "old-webhook-token")
        # A provider that worked keeps working: connected, config checked.
        self.assertEqual(connection.state, "connected")
        _adapter_class, config = provider._brbank_prepare_adapter()
        self.assertEqual(config.numero_cliente, 9)
        self.assertEqual(event.connection_id, connection)
        # Running again changes nothing.
        self.assertEqual(self.migration.migrate_providers(self.env.cr), [])

    def test_enabled_provider_runs_in_production(self):
        provider = self._old_provider(
            "Old enabled",
            "enabled",
            brbank_client_id="id",
            brbank_client_secret="secret",
            brbank_extra_config=json.dumps({"numero_cliente": 1}),
        )
        self.migration.migrate_providers(self.env.cr)
        provider.invalidate_recordset()
        self.assertEqual(provider.brbank_connection_id.environment, "prod")

    def test_provider_never_configured_gets_no_connection(self):
        provider = self._old_provider("Old empty", "disabled")
        self.assertEqual(self.migration.migrate_providers(self.env.cr), [])
        provider.invalidate_recordset()
        self.assertFalse(provider.brbank_connection_id)

    def test_disabled_provider_with_events_keeps_its_history(self):
        provider = self._old_provider("Old with events", "disabled")
        event = self._old_event(provider, "B2")
        created = self.migration.migrate_providers(self.env.cr)
        event.invalidate_recordset()
        self.assertEqual(len(created), 1)
        self.assertEqual(event.connection_id.id, created[0])
        self.assertEqual(event.connection_id.state, "draft")

    def test_cnpj_of_the_settings_moves_to_the_connection(self):
        values = {
            "extra_config": json.dumps({"cnpj_empresa": "11222333000181", "a": 1})
        }
        self.migration._move_cnpj(values)
        self.assertEqual(values["cnpj"], "11222333000181")
        self.assertEqual(json.loads(values["extra_config"]), {"a": 1})
