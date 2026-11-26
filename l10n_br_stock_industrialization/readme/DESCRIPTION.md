Lado do industrializador na industrialização por encomenda: a empresa recebe
os insumos do cliente, industrializa, cobra o serviço e devolve o que não usou.

- **Recebimento dos insumos**: tipo de operação de estoque próprio, com a
  operação fiscal *Entrada para industrialização* (CFOP 1901/2901). O estoque
  recebido pertence ao cliente (dono) e o recebimento é marcado como
  industrialização. Um assistente a partir do pedido de venda cria o recebimento
  e outro atribui a uma venda um recebimento que chegou sem pedido.
- **Lotes**: todo item do recebimento de industrialização exige lote, os lotes
  de um mesmo recebimento são únicos e, ao concluir, ficam reservados à venda
  de origem. O lote também indica se é de industrialização.
- **Devolução do material não utilizado**: lista o estoque do cliente, separa
  os lotes para devolução e cria o retorno com o preço da nota de origem do
  lote, exigindo o dono do material.
- **Rota Apenas cobrança**: a venda fatura sem movimentar o estoque, só com a
  operação de serviço de industrialização; a linha do pedido informa o produto
  aplicado.
- **Mesclar movimentos**: opção na separação para manter os movimentos do mesmo
  produto separados.

As operações fiscais de serviço e de retorno de industrialização, com suas
linhas e tributações, são dados deste módulo (XML-ID estável), porque o
catálogo de operações da `l10n_br_fiscal` (OCA/l10n-brazil#5719) ainda não foi
mesclado. Quando for, o módulo migra para as operações do catálogo.
