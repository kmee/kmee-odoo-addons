# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Move the credentials of each brbank provider to a bank connection.

Before 16.0.2.0.0 the credentials, the refresh token and the webhook token
lived on the provider. They now live on `l10n_br_bank_connection.connection`,
shared by every domain that talks to the bank. The old columns stay in the
table (Odoo does not drop them): this script reads them with SQL.

- One connection per provider that matters: enabled or in test mode, with any
  credential typed, or with webhook events. A disabled provider that was never
  configured gets none (it needs one only to leave `disabled`).
- The webhook token is kept, so the URL registered at the bank keeps working
  through the alias route `/payment/brbank/webhook/<provider>/<token>`.
- The events received so far point to the connection of their provider.
"""

import base64
import json
import logging

from psycopg2 import sql

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# Column of `payment_provider` -> field of the connection.
TEXT_COLUMNS = {
    "brbank_client_id": "client_id",
    "brbank_client_secret": "client_secret",
    "brbank_username": "username",
    "brbank_password": "password",
    "brbank_pix_key": "pix_key",
    "brbank_refresh_token": "refresh_token",
    "brbank_extra_config": "extra_config",
    "brbank_secret_config": "secret_config",
    "brbank_webhook_token": "webhook_token",
}
BINARY_COLUMNS = {
    "brbank_certificate": "certificate",
    "brbank_private_key": "private_key",
}
# Columns that, when filled, show the provider was configured.
CREDENTIAL_COLUMNS = tuple(
    column
    for column in list(TEXT_COLUMNS) + list(BINARY_COLUMNS)
    if column != "brbank_webhook_token"
)


def _columns(cr, table):
    cr.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table,),
    )
    return {row[0] for row in cr.fetchall()}


def _move_cnpj(values):
    """`cnpj_empresa` typed in the settings becomes the CNPJ of the connection."""
    text = values.get("extra_config")
    if not text:
        return
    try:
        settings = json.loads(text)
    except ValueError:
        return
    if isinstance(settings, dict) and settings.get("cnpj_empresa"):
        values["cnpj"] = str(settings.pop("cnpj_empresa"))
        values["extra_config"] = json.dumps(settings, indent=2, sort_keys=True)


def migrate_providers(cr):
    """Create the connections and point providers and events to them.

    Split from `migrate` so a test can run it over data it assembled.

    :return: Ids of the connections created.
    """
    env = api.Environment(cr, SUPERUSER_ID, {"tracking_disable": True})
    existing = _columns(cr, "payment_provider")
    old = [c for c in list(TEXT_COLUMNS) + list(BINARY_COLUMNS) if c in existing]
    columns = ["id", "name", "company_id", "state", "brbank_adapter"]
    if "brbank_pix_perfil" in existing:
        columns.append("brbank_pix_perfil")
    columns += old
    cr.execute(
        sql.SQL(
            "SELECT {} FROM payment_provider "
            "WHERE code = 'brbank' AND brbank_connection_id IS NULL ORDER BY id"
        ).format(sql.SQL(", ").join(sql.Identifier(c) for c in columns))
    )
    created = []
    for row in cr.dictfetchall():
        cr.execute(
            "SELECT 1 FROM l10n_br_brbank_event WHERE provider_id = %s LIMIT 1",
            (row["id"],),
        )
        has_events = bool(cr.fetchone())
        configured = any(row.get(column) for column in CREDENTIAL_COLUMNS)
        if not row["brbank_adapter"]:
            continue
        if row["state"] == "disabled" and not configured and not has_events:
            continue
        name = row["name"]
        if isinstance(name, dict):  # translated column (jsonb)
            name = name.get("en_US") or next(iter(name.values()), "")
        values = {
            "name": name,
            "company_id": row["company_id"],
            "adapter": row["brbank_adapter"],
            "pix_profile": row.get("brbank_pix_perfil") or False,
            "environment": "prod" if row["state"] == "enabled" else "test",
        }
        for column, field_name in TEXT_COLUMNS.items():
            if row.get(column):
                values[field_name] = row[column]
        for column, field_name in BINARY_COLUMNS.items():
            if row.get(column):
                values[field_name] = base64.b64encode(bytes(row[column]))
        _move_cnpj(values)
        try:
            with cr.savepoint():
                connection = env["l10n_br_bank_connection.connection"].create(values)
        except Exception:  # pylint: disable=broad-except
            _logger.exception(
                "brbank migration: could not create the connection of provider %s",
                row["id"],
            )
            continue
        # Created as a draft (a connection checks its configuration only
        # once it is connected); a provider that worked keeps working.
        cr.execute(
            "UPDATE l10n_br_bank_connection_connection SET state = %s WHERE id = %s",
            ("draft" if row["state"] == "disabled" else "connected", connection.id),
        )
        cr.execute(
            "UPDATE payment_provider SET brbank_connection_id = %s WHERE id = %s",
            (connection.id, row["id"]),
        )
        created.append(connection.id)
    cr.execute(
        """
        UPDATE l10n_br_brbank_event event
           SET connection_id = provider.brbank_connection_id
          FROM payment_provider provider
         WHERE event.provider_id = provider.id
           AND event.connection_id IS NULL
           AND provider.brbank_connection_id IS NOT NULL
        """
    )
    return created


def migrate(cr, version):
    if not version:
        return
    migrate_providers(cr)
    # Events are deduplicated by connection now.
    cr.execute(
        "ALTER TABLE l10n_br_brbank_event "
        "DROP CONSTRAINT IF EXISTS l10n_br_brbank_event_event_unique"
    )
    # The column was added without NOT NULL (the rows had no connection yet).
    try:
        with cr.savepoint():
            cr.execute(
                "ALTER TABLE l10n_br_brbank_event "
                "ALTER COLUMN connection_id SET NOT NULL"
            )
    except Exception:  # pylint: disable=broad-except
        _logger.warning(
            "brbank migration: events without a connection remain; "
            "connection_id stays nullable"
        )
