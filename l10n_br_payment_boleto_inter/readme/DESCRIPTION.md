Emite boletos de cobrança registrada pela API v3 do Banco Inter e acompanha o
pagamento, como um provedor de pagamento (`payment.provider`) do Odoo.

O boleto é gerado a partir de uma transação de pagamento (fatura ou pedido de
venda), com os dados do pagador, vencimento, desconto, multa e juros do modo de
pagamento. O PDF fica guardado na transação e pode ser impresso pelo menu
Imprimir da fatura e do pedido, ou aberto pelo portal com o token de acesso.

Um agendamento consulta o banco e confirma (ou cancela) a transação conforme a
situação do boleto, o que dispara a conciliação do pagamento.
