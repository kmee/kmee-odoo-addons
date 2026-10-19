Este módulo adiciona o tipo de comissão **Faixas por período** (*period
section*). A porcentagem não depende de cada linha isolada, e sim do total
vendido pelo agente dentro do período da liquidação: quanto maior o total,
maior a faixa atingida, e a porcentagem dessa faixa vale para todas as linhas
do período.

Exemplo de faixas:

* Até R$ 10.000,00: 2%
* De R$ 10.000,01 até R$ 20.000,00: 3%
* De R$ 20.000,01 até R$ 99.999.999,00: 4% (a última faixa precisa de um limite alto)

Ao gerar a liquidação, o sistema soma a base de todas as linhas da liquidação
(valor bruto ou margem, conforme a comissão), descobre a faixa atingida e
grava o valor liquidado de cada linha. Devoluções entram com sinal negativo.
Até a liquidação, a fatura mostra a comissão provisória pela primeira faixa.
