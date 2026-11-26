Guarda no lote de estoque o número, a nota fiscal e a linha da nota fiscal de
origem, além da compra, da venda e do recebimento que o originaram. O nome do
lote recebe o documento de origem como sufixo (`L001 [PO0001]`) e o lote criado
no recebimento herda a nota e a linha da nota do movimento de estoque.

A linha do documento fiscal também guarda a nota e a linha da nota de origem:
ao faturar uma entrega, a linha da fatura herda os dados do movimento de estoque.

O recebimento também pode ser preenchido a partir de uma NF-e de entrada: o
botão **Preencher por NF-e** liga cada linha da nota ao movimento do mesmo
produto (criando-o se não existir) e propõe os lotes dos produtos rastreados
por lote.
