1. Receba os insumos do cliente com lote e nota de origem (módulo
   `l10n_br_stock_industrialization`).
2. Produza com uma ordem de produção que consuma os insumos do cliente (dono do
   estoque = cliente) e a matéria-prima da empresa, e conclua a ordem.
3. Entregue o produto industrializado em uma separação com a operação fiscal
   *Serviço de Industrialização*, ligada à ordem de produção.
4. Na separação concluída, use *Criar fatura*. A fatura traz a linha do
   produto entregue, o retorno do material utilizado e o serviço sobre a
   matéria-prima aplicada.
5. Se cancelar a fatura, o consumo das ordens volta a ficar disponível para
   uma nova fatura.

Na base de demonstração, a entrega `OS-2026-0152` já está concluída e pronta
para faturar.
