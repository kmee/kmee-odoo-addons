- Receber a situação do boleto por webhook do Inter, com validação de
  assinatura, em vez de depender só do agendamento a cada 30 minutos.
- Conferir o valor recebido (`valorTotalRecebido`) contra o valor da transação
  antes de confirmar o pagamento.
