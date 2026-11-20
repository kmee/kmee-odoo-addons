O fornecedor responde a cotação da rodada (``purchase_rfq_round``) pelo portal.

* o e-mail da cotação, enviado pela rodada, traz o botão de acesso ao portal
  (link com token: o fornecedor não precisa de usuário; usuários do portal
  também acessam por "Minha conta");
* na cotação, o portal mostra a rodada, o prazo de resposta e o botão
  "Responder a cotação";
* o fornecedor preenche preço, prazo de entrega e observação por item (deixa o
  preço vazio nos itens que não fornece) e envia; pode corrigir até o prazo;
* a resposta é gravada na cotação e no histórico da rodada (origem "Portal"),
  e o comprador é avisado no chatter da cotação e da rodada;
* depois do prazo de resposta, com a rodada fechada ou a cotação confirmada, a
  página fica só para leitura;
* validação no servidor: preço e prazo numéricos e não negativos; ou grava a
  resposta inteira, ou nada.

Os campos da resposta são extensíveis (``_rfq_portal_line_fields``):
``purchase_rfq_comparison_portal`` acrescenta condição de pagamento, validade,
lote mínimo e especificação.
