In the form view of the **Payment Transaction**, boleto-related fields will be displayed if the transaction corresponds to a boleto payment.

Each boleto charges one installment of the invoice, shown in the field **Installment**. When the boleto is paid, the payment is reconciled with that installment only, so a boleto paid out of order does not settle another installment. Generating the boletos again skips the installments that already have a live boleto (draft, pending, authorized or done); an installment whose boleto failed or was canceled gets a new one.

A boleto is not a card payment, and the provider modules reuse the actions of the payment transaction with another meaning:

- **Capture** queries the status of the boleto in the bank and updates the transaction (registered, paid, written off). Nothing is captured.
- **Void** and **Refund** ask the bank to write off (cancel) the boleto. A boleto that was already paid is not refunded by the bank: the money must be returned to the payer outside the boleto.

This mapping is temporary, until a dedicated model of bank instructions (write-off, due date extension, discount, protest) replaces it.
