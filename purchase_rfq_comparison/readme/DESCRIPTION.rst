Comparação multicritério das respostas de uma rodada de cotação
(``purchase_rfq_round``).

O core compara só o subtotal sem impostos e a data prevista. Para compra
industrial no Brasil isso não basta: IPI e ST por fora, prazo de pagamento,
validade da proposta, lote mínimo e homologação do fornecedor mudam a decisão.

Este módulo acrescenta:

* homologação do fornecedor por produto (``product.supplierinfo``);
* campos de resposta na linha da cotação: condição de pagamento, validade, lote
  mínimo e "atende a especificação" (padrão: fornecedor homologado);
* prazo médio de pagamento e valor presente do total com impostos, pela
  condição respondida e pela taxa mensal da rodada;
* pontuação de 0 a 100 por item, com base de preço configurável (subtotal,
  total com impostos ou valor presente) e pesos de preço e prazo; respostas
  vencidas, ou de fornecedor não homologado quando a rodada exige, não pontuam;
* "Adjudicar melhor pontuação" na rodada; pontuação e valor presente na
  comparação e na matriz fornecedor x item;
* as colunas novas na planilha de resposta e na importação.

Limite conhecido: o preço é comparado pelo total com impostos ou pelo subtotal.
A comparação pelo custo líquido de créditos (ICMS, PIS e COFINS recuperáveis)
depende da pilha de custo líquido da localização brasileira, que ainda não
existe na 18.0.
