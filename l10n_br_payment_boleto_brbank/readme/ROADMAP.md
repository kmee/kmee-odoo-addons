- **No adapter of the brbank library has been validated in a bank sandbox yet**
  (`validado_sandbox = False` in all of them). Inter and PinBank were ported
  from modules running in production, the others were built from public
  documentation. The provider form and the payment mode warn about it. Test
  each bank with low amounts before production.
- The minimum version of brbank is 0.0.3 (adapters of Itaú, Bradesco,
  Santander, BTG Pactual, C6 Bank, Banrisul, Unicred, Caixa and Safra), not on
  PyPI yet; 0.0.2, on PyPI, runs on Python 3.10 but has the first five banks
  only. The manifest names the package without a version (a specifier there
  breaks the import check), so the minimum is not enforced at install.
- The registration runs in the transaction that posts the invoice. If that
  transaction is rolled back after the bank answered, the bank keeps the
  title; the next attempt sends the same idempotency key (Pix answers
  `Duplicado` and the title is read back), but a boleto bank that does not
  deduplicate by our reference may keep an orphan title.
- Webhooks are only parsed for the banks whose adapter declares them (Inter,
  Sicredi, BTG Pactual, C6 Bank, Unicred and the Pix profiles); the others
  rely on the reconciliation cron.
- The nosso numero generators of the adapters (`gerar_nosso_numero`) are not
  exposed: the numeric reference of the transaction (installment id plus a
  two digit attempt) is used. Banks with a short nosso numero (Itaú 8 digits,
  Safra 9, Banco do Brasil 10) refuse it once the ids grow; a sequence per
  provider is the next step. Banrisul without a generator lets the bank
  number the title, so a registration repeated after a network failure may
  issue it twice.
- BTG Pactual: the authorization code flow (consent at the BTG Id) is done
  outside Odoo. Two calls renewing the same refresh token at the same time
  (two workers) may leave one of them with a token the bank already replaced.
- Caixa has no test environment: the provider cannot use the test mode.
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
