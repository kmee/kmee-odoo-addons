Gestao completa do ciclo de venda em caminhoes/vans integrado ao Odoo POS.

O modulo gerencia todo o fluxo operacional de vendas em vans: carregamento de
produtos no armazem, vendas pelo POS durante a rota, conferencia do retorno e
fechamento contabil com apuracao de diferencas de estoque e caixa.

Principais funcionalidades:

* **Sessoes Van** com maquina de estados completa:
  Rascunho -> Em Carregamento -> Carregado -> Em Rota -> Retornado -> Fechado
* **Estoque residual**: produtos nao vendidos permanecem no caminhao e sao
  automaticamente carregados na sessao seguinte (carry-over)
* **Integracao POS**: abertura e fechamento do POS vinculados a sessao van,
  com captura automatica de vendas, devolucoes e pagamentos
* **Pickings automaticos**: carga (armazem -> van) e descarga (van -> armazem)
  com rastreabilidade completa via stock.move.line
* **Apuracao de diferencas**: calculo automatico de diferencas de estoque
  (qty_diff) e caixa (cash_diff) por sessao
* **Lancamento contabil**: geracao automatica de account.move no fechamento,
  debitando o motorista por diferencas nao abonadas
* **Abono de diferencas**: possibilidade de abonar diferencas de estoque com
  justificativa obrigatoria (minimo 20 caracteres)
* **Multiplos metodos de pagamento**: suporte a dinheiro, cartao, transferencia
  bancaria e conta do cliente (pay later) por POS
* **Relatorios**: analise de vendas, desempenho por motorista, movimentacao de
  produtos e controle de diferencas via pivot/graph
* **Lista de precos**: preco unitario das linhas calculado pela pricelist
  configurada no POS, propagado para os stock.moves (valorizacao)
