Escolhe de qual fornecedor sai o prazo (DLT) do item comprado no buffer DDMRP.

O ddmrp usa o prazo do primeiro fornecedor da lista (sequência, quantidade
mínima, preço). Com rodada de cotação, o vencedor pode ser outro fornecedor,
com prazo maior: o buffer fica subdimensionado e o recebimento cai fora da
janela do DLT.

O perfil de buffer ganha a opção "Fornecedor para o DLT":

* primeiro da lista (padrão do ddmrp);
* pior prazo entre os fornecedores homologados (``purchase_rfq_comparison``);
  sem homologado, considera todos;
* pior prazo entre todos os fornecedores.
