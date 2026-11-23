Coloca os pedidos de compra confirmados no fluxo de caixa previsto, na data de
vencimento.

Pedido de compra confirmado não gera lançamento contábil: até virar fatura, ele
não aparece no fluxo de caixa do MIS Builder (``mis_builder_cash_flow``). O
módulo ``mis_builder_total_committed_purchase`` (OCA) mostra o comprometido
orçamentário, na data de entrega e na conta de despesa; para o caixa faltam o
vencimento, os impostos e o abatimento do que já foi faturado.

Este módulo mantém a tabela "Compras comprometidas a pagar", fonte "parecida com
lançamento" para o MIS Builder (``date``, ``account_id``, ``debit``,
``credit``, ``company_id``):

* uma linha por parcela de cada pedido confirmado, pela condição de pagamento
  do pedido, a partir da data prevista de recebimento;
* valor = saldo ainda não faturado, com impostos, na moeda da empresa, no
  crédito da conta a pagar do fornecedor;
* atualizada ao confirmar, alterar ou cancelar o pedido e ao lançar, voltar a
  rascunho ou cancelar a fatura do fornecedor; um cron diário ressincroniza
  tudo.
