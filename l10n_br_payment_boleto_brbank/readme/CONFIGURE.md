1. Install the `brbank` Python library in the Odoo environment
   (`pip install brbank`). It needs Python 3.10 or later.
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
4. Set the provider to *Test Mode* (bank sandbox) or *Enabled* (production) and
   choose its journal in the *Configuration* tab. The provider refuses to leave
   *Disabled* while a required key is missing.
5. In the payment mode (*Invoicing > Configuration > Payment Modes*), tick
   *Generate boletos on invoice?* and choose the provider. The payment mode
   shows what the bank supports.

Only users of *Administration / Settings* see and edit the credentials. The
webhook token travels in the URL: mask it in the logs of the reverse proxy.

Crons:

- *Boleto brbank: reconcile titles with the banks*, every 30 minutes, the same
  period of the Inter and PinBank modules, so the delay between payment and
  settlement does not get worse. Lengthen it only when the webhook of every
  bank in use is validated in production.
- *Boleto brbank: process bank webhook events*, triggered by every webhook call
  and every 10 minutes as a fallback.
