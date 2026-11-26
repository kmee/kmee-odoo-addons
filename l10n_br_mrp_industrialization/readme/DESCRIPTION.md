Fatura da industrialização por encomenda a partir das ordens de produção, do
lado do industrializador.

Ao faturar a entrega do produto industrializado (operação de serviço de
industrialização ou de serviço por conta e ordem), a fatura recebe também, a
partir das ordens de produção que originaram a entrega:

- **Retorno do material utilizado**: o material do cliente consumido na ordem
  (dono do estoque = cliente), pelo preço da linha da nota fiscal de origem do
  lote, com a linha de operação *Retorno do material utilizado*.
- **Serviço sobre a matéria-prima aplicada**: a matéria-prima da própria
  empresa consumida na ordem, pelo preço da linha do pedido de venda na rota
  *Apenas cobrança*, com a linha de operação *Serviço de industrialização -
  Matéria-prima*.

Linhas iguais (produto, preço e linha de operação) são somadas em uma só. Cada
linha da fatura guarda os consumos das ordens que a geraram; o consumo já
faturado não entra em outra fatura, e volta a ficar em aberto quando a fatura é
cancelada ou apagada. A lista de faturas mostra as ordens de produção de cada
fatura.
