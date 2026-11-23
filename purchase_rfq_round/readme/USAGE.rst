#. Em Compras > Requisições > Linhas, selecione as linhas aprovadas e use
   "Criar rodada de cotação" (menu Ação).
#. Na rodada, confira os itens e os fornecedores e clique em "Criar cotações".
#. "Enviar por e-mail" manda cada cotação pelo e-mail padrão de cotação.
#. Lance os preços e prazos respondidos em cada cotação (ou importe a planilha,
   com ``purchase_rfq_round_sheet``).
#. "Comparar" abre as respostas por item, com a vencedora em destaque, e a
   matriz fornecedor x item. Adjudique por item, ou use "Adjudicar melhor
   preço" ou "Adjudicar melhor prazo".
#. Se quiser negociar de novo, "Nova rodada" cancela as cotações desta e abre a
   rodada seguinte com o melhor preço como referência.
#. "Fechar rodada" cancela as cotações perdedoras e deixa as vencedoras prontas
   para confirmar (com a alçada do pedido, se houver).

O limite de linhas para criar as cotações em fila está no parâmetro de sistema
``purchase_rfq_round.job_threshold`` (padrão 2000 = itens x fornecedores).
