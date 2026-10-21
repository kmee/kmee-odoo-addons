- Na fatura de cliente, com o modo de pagamento do Inter, ao confirmar a fatura
  (ou pelo botão de gerar boletos) é criada uma transação para cada vencimento
  em aberto e o boleto é registrado no Banco Inter. Gerar de novo não duplica
  boletos que já existem.
- Cada boleto fica ligado à sua parcela (campo **Installment** da transação). Pago
  o boleto, o pagamento é conciliado só com essa parcela, mesmo que o cliente
  pague fora de ordem.
- Imprima o boleto pelo menu Imprimir da fatura ou do pedido de venda; faturas
  parceladas saem com todos os boletos num só arquivo.
- Para cancelar, use a ação de cancelar na transação: o boleto é cancelado no
  banco e a transação fica cancelada.
- O agendamento *Atualizar status de boletos Inter* confirma a transação quando
  o boleto é pago.
