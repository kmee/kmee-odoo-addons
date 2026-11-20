Faz o buffer DDMRP contar uma vez a quantidade cotada com vários fornecedores.

O ddmrp soma no "em andamento" todas as linhas de cotação ligadas ao buffer.
Numa rodada de cotação (``purchase_rfq_round``) ou num grupo de Alternativas do
core, a mesma necessidade aparece uma vez por fornecedor, e o buffer enxergaria
a quantidade multiplicada pelo número de fornecedores.

Com o módulo:

* fica uma linha por item da rodada (ou por produto do grupo de Alternativas):
  a vencedora, se houver; senão a de maior quantidade e entrega mais cedo;
* a escolha é feita antes do corte pela janela do DLT, para que fornecedores
  com prazos diferentes não contem a mesma necessidade duas vezes;
* a requisição de compra que já está numa rodada com cotações criadas deixa de
  ser contada pela requisição (``ddmrp_purchase_request``), porque passa a ser
  contada pelas cotações.

Instala sozinho quando ``ddmrp_purchase_request`` e ``purchase_rfq_round``
estão instalados.
