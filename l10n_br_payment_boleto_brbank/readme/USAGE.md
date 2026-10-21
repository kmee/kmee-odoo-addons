Issuing:

- Post a customer invoice whose payment mode generates boletos with a brbank
  provider: one transaction per open installment is created and registered at
  the bank. *Generate boletos* again only issues the installments without a
  live title.
- If the bank is unavailable, the transaction stays in draft with the reason
  and the reconciliation cron registers it later with the same idempotency key.
  If the bank refuses the data, the posting stops with the reason, naming the
  missing customer fields.
- The invoice PDF and the portal show, per open title, the due date, the
  amount, the digitable line and the Pix copy and paste (with its QR code). The
  portal also offers the boleto PDF when the bank provides one.

Following up, in the transaction:

- *Check at the bank* reads the title back and applies its status. The
  *Capture* button of `payment` does the same, and *Void* writes the title off.
- *Bank instruction* sends a due date extension, a rebate, a protest or a credit
  bureau report; *Write off at the bank* cancels the title. The buttons only
  show when the bank declares the capability; a command the bank refuses stays
  recorded as rejected, with the reason.
- For BTG Pactual, the *Refresh Token* of the provider changes by itself after
  the calls to the bank: the provider keeps the last token the bank returned.
- *Invoicing > Customers > Boleto Instructions* lists every instruction, and
  *Invoicing > Configuration > Payments > Bank Webhook Events* every event
  received (managers only).

Return files (CNAB): a module that reads a return file of an account that also
uses the API can call `payment.transaction._brbank_notify_cnab_occurrence(
nosso_numero, company)`: the transaction is found by its nosso numero and read
back from the bank, so the file and the API never settle the same title twice.

Moving from `l10n_br_payment_boleto_inter` or `l10n_br_payment_boleto_pinbank`:

1. Configure the brbank provider of the same bank (*Banco Inter (Boleto)* or
   *PinBank (Boleto)*) with the credentials of the old provider.
2. In the payment mode, replace the old provider by the brbank one in
   *Payment provider*: this single field links the payment mode to the bank.
3. New invoices are issued through brbank. The titles issued before stay with
   the old provider and its cron until they are paid or written off; uninstall
   the old module only after that.
