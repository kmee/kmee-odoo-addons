1. Install the `brbank` Python library in the Odoo environment
   (`pip install "brbank>=0.0.3"`). It needs Python 3.10 or later. Version
   0.0.3 is the minimum: it brings the adapters of Itaú, Bradesco, Santander,
   BTG Pactual, C6 Bank, Banrisul, Unicred, Caixa and Safra (the manifest only
   names the package, so the version is not checked at install).
2. Go to *Invoicing > Configuration > Payment Providers* and open the provider
   of the bank (for instance *Sicoob (Boleto)* or *Pix Itaú*).
3. In the *Credentials* tab:
   - the bank adapter (and the Pix profile) are already set by the data;
   - fill the credentials the adapter asks for (client id and secret, API
     user and password, certificate and private key in PEM, Pix key). Only the
     fields the adapter uses are shown;
   - click *Fill settings template* and complete the JSON of *Extra Settings*
     (agreement, wallet, client number and so on) and *Extra Secrets* (developer key,
     API key and so on). *Settings Keys* lists every key with its type, which ones are
     required and which ones are secret;
   - if the bank has a webhook, register the *Webhook URL* at the bank. *Rotate
     webhook token* issues a new URL and stops the old one at once.
   - keys typed as a function in the library (`gerar_nosso_numero`,
     `ao_renovar_refresh_token`) never go in the JSON: the nosso numero is the
     numeric reference of the transaction (installment and attempt), and the
     refresh token is handled by the provider (see below).
4. Set the provider to *Test Mode* (bank sandbox) or *Enabled* (production) and
   choose its journal in the *Configuration* tab. The provider refuses to leave
   *Disabled* while a required key is missing.
5. In the payment mode (*Invoicing > Configuration > Payment Modes*), tick
   *Generate boletos on invoice?* and choose the provider. The payment mode
   shows what the bank supports.

Notes per bank:

- **BTG Pactual**: the API only accepts tokens of the authorization code flow,
  done once at the BTG Id outside Odoo. Paste the refresh token it gives in
  *Refresh Token*. The bank may return a new refresh token at each renewal and
  invalidate the old one: the provider saves it at once, in a database
  transaction of its own, so an error or a rollback of the operation never
  loses it. A refresh token unused for more than 10 days expires and the
  consent must be done again. Use each BTG credential in one database only.
  Fill `dias_expiracao` (days after the due date until the title expires), or
  the bank refuses titles without an automatic write-off term.
- **Caixa**: there is no public test environment, so the provider refuses the
  *Test Mode*. Enable it and validate with a title of low amount.
  `documento_beneficiario` is a secret key (*Extra Secrets*).
- **C6 Bank**: the Pix key must be a random key (EVP); the bank silently issues
  a boleto without Pix with any other kind.
- **Itaú**: `bolecode` (hybrid boleto) is on by default and needs the Pix key.
- **Santander**: the Pix key needs `tipo_chave_pix` (EMAIL, CPF, CNPJ, CELULAR
  or EVP); `workspace_id` is the billing workspace created at the bank.
- **Bradesco**: `documento_beneficiario` is a secret key (*Extra Secrets*).
- **Banrisul**: without `gerar_nosso_numero` the bank generates the nosso
  numero.
- **Unicred**: `api_key` and the two webhook keys go in *Extra Secrets*.
- **Safra**: the bank declares no capability (no write-off, instruction, PDF
  nor webhook): titles are followed by the reconciliation cron only.

Only users of *Administration / Settings* see and edit the credentials. The
webhook token travels in the URL: mask it in the logs of the reverse proxy.

Crons:

- *Boleto brbank: reconcile titles with the banks*, every 30 minutes, the same
  period of the Inter and PinBank modules, so the delay between payment and
  settlement does not get worse. Lengthen it only when the webhook of every
  bank in use is validated in production.
- *Boleto brbank: process bank webhook events*, triggered by every webhook call
  and every 10 minutes as a fallback.
