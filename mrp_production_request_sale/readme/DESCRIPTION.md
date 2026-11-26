Liga o pedido de produção (`mrp_production_request`) à venda que o originou.

- O pedido de produção mostra a venda de origem, o cliente, o vendedor e as notas de produção da linha da venda.
- A linha da venda pode indicar uma lista de materiais explícita, que vale tanto para o pedido de produção quanto para a ordem de produção.
- A ordem de produção criada a partir do pedido de produção fica ligada à linha da venda.
- Quando o componente de uma ordem de produção também é fabricado, a necessidade vira uma ordem de produção (sub-OP) em vez de um novo pedido de produção.
- Linhas adicionadas depois da confirmação da venda são marcadas, assim como os movimentos de estoque que elas geram.
