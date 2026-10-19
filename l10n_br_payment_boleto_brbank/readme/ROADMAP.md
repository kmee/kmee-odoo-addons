- **No adapter of the brbank library has been validated in a bank sandbox yet**
  (`validado_sandbox = False` in all of them). Inter and PinBank were ported
  from modules running in production, the others were built from public
  documentation. The provider form and the payment mode warn about it. Test
  each bank with low amounts before production.
- brbank 0.0.1 on PyPI requires Python 3.11 and `cryptography>=50`, which
  cannot be installed next to Odoo 16.0 (Python 3.10, pyOpenSSL 22). The
  branch `fix/py310-odoo16` of the library makes it run on Python 3.10 with
  `cryptography>=38`; a release with it is needed before production.
- The registration runs in the transaction that posts the invoice. If that
  transaction is rolled back after the bank answered, the bank keeps the
  title; the next attempt sends the same idempotency key (Pix answers
  `Duplicado` and the title is read back), but a boleto bank that does not
  deduplicate by our reference may keep an orphan title.
- Webhooks are only parsed for the banks whose adapter declares them (Inter,
  Sicredi and the Pix profiles); the others rely on the reconciliation cron.
- The webhook events are processed by `ir.cron` with an immediate trigger, not
  by `queue_job`, so the module adds no dependency; move to `queue_job` if a
  bank sends large volumes.
- The CNAB bridge is a hook (`_brbank_notify_cnab_occurrence`): no return file
  module calls it yet.
- The brbank providers are left out of the online checkout: the redirect and
  token flows of `payment` are not implemented for them.
- The credentials are stored in the database, restricted to the settings
  group; a vault (Vault, KMS) is a decision still open.
- The reconciliation cron queries each open title; banks with batch queries or
  movement statements could be read in one call per account.
- No alert yet for certificates close to expiry.
- The provider records use the module icon; the logos of the banks are not shipped.
