# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Access tokens shared between the workers of Odoo, kept in the database.

The bank (BTG) rotates the refresh token at each renewal and invalidates the
old one, so two processes renewing at the same time lose the token: the one
that renews last uses a value already dead. `OdooTokenStore` implements the
`ArmazemToken` of the library (`brbank.auth`): the renewal runs under a lock
of the database, the access token lives in a table, and each process reads it
again after taking the lock, before asking the bank for a new one.

Everything here runs in the thread of the bank call (or in the threads the
library spawns for the store), never in the environment of the caller: it
opens cursors of its own from the registry and commits them. The caller can
hold uncommitted rows or row locks without ever being waited on.
"""

import logging
import threading
from dataclasses import dataclass

import psycopg2

try:
    from brbank.auth import TokenPersistido
except ImportError:  # pragma: no cover - the library before 0.0.6

    @dataclass(frozen=True)
    class TokenPersistido:
        valor: str
        expira_em: float


_logger = logging.getLogger(__name__)

TOKEN_TABLE = "l10n_br_bank_connection_token"
CONNECTION_TABLE = "l10n_br_bank_connection_connection"

# Locks of this process, by (database, connection, key). They keep the threads
# of one worker from each holding a database connection while they wait for
# the lock of the database; they also tolerate being released by another
# thread than the one that took them (the library enters and leaves the lock
# in different threads of its executor).
_PROCESS_LOCKS = {}
_PROCESS_LOCKS_GUARD = threading.Lock()


def _process_lock(dbname, connection_id, key):
    with _PROCESS_LOCKS_GUARD:
        return _PROCESS_LOCKS.setdefault((dbname, connection_id, key), threading.Lock())


def token_key(chave):
    """Text of the key of the library, a tuple `(account, scope or None)`."""
    return "|".join("" if part is None else str(part) for part in chave)


class _Lock:
    """Lock of the renewal: process lock plus `pg_advisory_xact_lock`.

    A class and not a `contextmanager` generator because the library calls
    `__enter__` and `__exit__` from different threads. The advisory lock is
    transactional: it lives in a cursor of its own and goes away when that
    cursor commits and closes, even if the process dies.
    """

    def __init__(self, store, key):
        self._store = store
        self._key = key
        self._local = _process_lock(store.dbname, store.connection_id, key)
        self._cr = None

    def __enter__(self):
        self._local.acquire()
        try:
            registry = self._store.registry
            # In test mode every cursor is a view of one connection: a lock of
            # the database would lock nothing, and the test cursor can only be
            # closed by the thread that opened it.
            if not registry.in_test_mode():
                self._cr = registry.cursor()
                self._cr.execute(
                    "SELECT pg_advisory_xact_lock(%s, hashtext(%s))",
                    (self._store.connection_id, self._key),
                )
        except BaseException:
            self._release()
            raise
        return None

    def __exit__(self, exc_type, exc, traceback):
        self._release()
        return False

    def _release(self):
        cr, self._cr = self._cr, None
        try:
            if cr is not None:
                try:
                    cr.commit()  # pylint: disable=invalid-commit
                finally:
                    cr.close()
        finally:
            self._local.release()


class OdooTokenStore:
    """`ArmazemToken` of the brbank library on top of the Odoo database.

    :param registry: Registry of the database; cursors come from it.
    :param int connection_id: `l10n_br_bank_connection.connection` that owns
        the tokens.
    """

    def __init__(self, registry, connection_id):
        self.registry = registry
        self.dbname = registry.db_name
        self.connection_id = connection_id

    def ler(self, chave):
        """Token stored for `chave`, or None. Never raises: it is a cache."""
        try:
            with self.registry.cursor() as cr:
                cr.execute(
                    f"SELECT value, expires_at FROM {TOKEN_TABLE} "  # noqa: S608
                    "WHERE connection_id = %s AND key = %s",
                    (self.connection_id, token_key(chave)),
                    log_exceptions=False,
                )
                row = cr.fetchone()
        except psycopg2.Error as error:
            _logger.warning(
                "bank connection %s: could not read the token (%s)",
                self.connection_id,
                type(error).__name__,
            )
            return None
        if not row or not row[0]:
            return None
        return TokenPersistido(valor=row[0], expira_em=float(row[1]))

    def gravar(self, chave, token):
        """Upsert and commit the token. A failure only costs one more renewal."""
        try:
            with self.registry.cursor() as cr:
                cr.execute(
                    f"INSERT INTO {TOKEN_TABLE} "  # noqa: S608
                    "(connection_id, key, value, expires_at, create_date, write_date) "
                    "VALUES (%s, %s, %s, %s, now() AT TIME ZONE 'UTC', "
                    "now() AT TIME ZONE 'UTC') "
                    "ON CONFLICT (connection_id, key) DO UPDATE SET "
                    "value = EXCLUDED.value, expires_at = EXCLUDED.expires_at, "
                    "write_date = EXCLUDED.write_date",
                    (
                        self.connection_id,
                        token_key(chave),
                        token.valor,
                        float(token.expira_em),
                    ),
                    log_exceptions=False,
                )
        except psycopg2.Error as error:
            # Typically a connection not committed yet (foreign key). The
            # library keeps the token in memory anyway.
            _logger.warning(
                "bank connection %s: could not save the token (%s)",
                self.connection_id,
                type(error).__name__,
            )

    def trava(self, chave):
        """Context manager serializing the renewal of `chave` between processes."""
        return _Lock(self, token_key(chave))


def read_refresh_token(registry, connection_id, fallback=None):
    """Current refresh token of the connection, read in a cursor of its own.

    Called by the library inside the renewal lock: the value in memory may be
    old because another process already renewed and the bank rotated it.

    :param fallback: Returned when the row is not visible (connection not
        committed yet) or empty.
    """
    try:
        with registry.cursor() as cr:
            cr.execute(
                f"SELECT refresh_token FROM {CONNECTION_TABLE} "  # noqa: S608
                "WHERE id = %s",
                (connection_id,),
                log_exceptions=False,
            )
            row = cr.fetchone()
    except psycopg2.Error:
        return fallback
    return (row and row[0]) or fallback
