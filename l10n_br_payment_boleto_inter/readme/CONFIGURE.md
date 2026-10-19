Em Faturamento > Configuração > Provedores de pagamento, abra o provedor
**Banco Inter** e preencha (apenas usuários administradores veem estes campos):

- Conta corrente;
- Client ID e Client Secret da aplicação criada no Internet Banking do Inter
  (escopos de cobrança: leitura e escrita);
- Certificado e chave privada (PEM) emitidos pelo Inter para a aplicação.

Use o estado *Teste* para o ambiente sandbox do Inter e *Habilitado* para
produção. Depois, no modo de pagamento (Faturamento > Configuração > Modos de
pagamento), aponte o provedor Inter e informe desconto, multa e juros.
