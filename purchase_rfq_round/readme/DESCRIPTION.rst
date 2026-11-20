Rodada de cotação com vários fornecedores, a partir das requisições de compra
aprovadas.

O core do Odoo cota com vários fornecedores pelas "Alternativas" do pedido de
compra, mas não guarda a rodada: não há referência de preço, histórico das
respostas, vencedor por item nem saving, e o grupo de Alternativas some quando
sobra um pedido. Este módulo acrescenta a rodada por cima das Alternativas:

* cria a rodada a partir das linhas de requisição aprovadas, consolidando por
  produto, e sugere os fornecedores cadastrados nos produtos;
* cria uma cotação por fornecedor, todas no mesmo grupo de Alternativas (em
  fila, com ``queue_job``, acima de um número de linhas configurável);
* envia cada cotação pelo e-mail padrão de cotação; o fornecedor responde e o
  comprador lança os preços na cotação;
* compara as respostas por item (lista agrupada e matriz fornecedor x item) e
  adjudica por melhor preço, por melhor prazo ou manualmente, item a item;
* abre uma nova rodada com o melhor preço da anterior como referência;
* fecha a rodada: cancela as cotações sem item vencedor, tira das vencedoras os
  itens perdidos, liga as requisições só às linhas vencedoras e registra o
  saving sobre o preço de referência (último preço de compra ou da rodada
  anterior). As vencedoras seguem a aprovação normal do pedido;
* guarda as respostas de cada fornecedor ao fechar a rodada ou abrir a seguinte.

Módulos opcionais por cima deste:

* ``purchase_rfq_round_sheet``: planilha padrão de resposta no e-mail e
  importação da resposta (planilha padrão ou do fornecedor);
* ``purchase_rfq_comparison``: comparação multicritério e pontuação;
* ``ddmrp_purchase_request`` e ``ddmrp_purchase_rfq_round``: integração com
  buffers DDMRP.

A comparação usa campos gravados (preço sem impostos na moeda da empresa e data
prevista), e não o ``get_tender_best_lines`` do core, que recalcula todas as
linhas do grupo e não escala para rodadas de milhares de linhas.
