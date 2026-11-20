Planilha de resposta na rodada de cotação (``purchase_rfq_round``).

* o e-mail de cada cotação leva uma planilha padrão (xlsx) com os itens e as
  células de resposta liberadas (preço, prazo de entrega, observação);
* "Importar respostas" lê a planilha preenchida: a padrão, pela coluna ID, ou a
  planilha do próprio fornecedor, com reconhecimento de cabeçalho por sinônimo,
  abreviação e pontuação ("Valor Unit. (R$)", "Cód.", "Cond. Pgto") e
  mapeamento manual de colunas;
* cada linha importada vira uma resposta guardada, com o arquivo e os valores
  como vieram.

As colunas da planilha e da importação são extensíveis
(``_get_sheet_columns`` e ``_get_import_columns``):
``purchase_rfq_comparison_sheet`` acrescenta condição de pagamento, validade,
lote mínimo e especificação.
