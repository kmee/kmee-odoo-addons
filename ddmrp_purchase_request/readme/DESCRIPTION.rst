Liga as requisições de compra (``purchase_request``) aos buffers DDMRP.

Quando o produto tem a opção "Purchase Request", o botão de reposição do buffer
cria uma requisição de compra em vez de uma cotação. Sem este módulo o buffer
não enxerga essa requisição e continua recomendando a mesma quantidade enquanto
ela espera aprovação ou cotação.

Com o módulo:

* a linha da requisição guarda o buffer de origem;
* a quantidade da requisição que ainda não virou cotação ou pedido é descontada
  da recomendação de reposição do buffer (como já acontece com as cotações);
* o buffer mostra a quantidade requisitada e abre as linhas de requisição.
