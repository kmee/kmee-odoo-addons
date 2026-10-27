**Necessidade:** a KMEE atende clientes que cobram por boleto no Banco Inter e
precisam emitir, imprimir e conciliar os boletos sem sair do Odoo.

**Abordagem:** integração direta com a API v3 de cobrança do Inter (OAuth2 com
certificado de cliente), sobre o módulo base `l10n_br_payment`, que já
define o contrato dos provedores de boleto. É um caminho diferente da remessa
CNAB (`l10n_br_account_payment_order`): aqui o registro e a baixa são online.

**Relacionados:** `l10n_br_payment` (base) e
`l10n_br_payment_pinbank` (outro provedor, mesmo contrato).
