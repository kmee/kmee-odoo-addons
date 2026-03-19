Configuracao inicial
~~~~~~~~~~~~~~~~~~~~

1. **Armazens (Warehouses)**

   Crie um armazem para cada caminhao/van em *Inventario > Configuracao > Armazens*.
   Configure o campo "Resupply From" apontando para o armazem principal (WH).
   Isso garante que o estoque flua do armazem central para a van.

   Exemplo::

       Van 01 - Joao   (VAN01)  ← resupply de WH
       Van 02 - Carlos  (VAN02)  ← resupply de WH
       Van 03 - Maria   (VAN03)  ← resupply de WH

2. **Tipos de Picking (Carga e Descarga)**

   Para cada van, crie dois tipos de operacao interna em
   *Inventario > Configuracao > Tipos de Operacoes*:

   * **Carga**: origem = estoque WH, destino = estoque da van
   * **Descarga**: origem = estoque da van, destino = estoque WH

3. **Contas Contabeis**

   Crie ou identifique 3 contas para o fechamento contabil:

   * **Motoristas Van - A Receber** (asset_receivable, reconcile=True):
     debitos por diferencas de estoque e caixa do motorista
   * **Mercadoria em Transito Van** (asset_current):
     credito pela diferenca de estoque (mercadoria que saiu e nao voltou)
   * **Caixa Van** (asset_current):
     credito/debito pela diferenca de caixa

4. **Diario Contabil**

   Crie um diario do tipo "Diversos" (general) para os lancamentos de
   fechamento de sessao, ex: "Diario Van Sales" (VAN).

5. **Diarios de Caixa**

   Cada POS precisa de um diario de caixa exclusivo (exigencia do Odoo).
   Crie um diario tipo "cash" para cada van, ex: "Caixa Van 01" (CV01).

6. **Metodos de Pagamento**

   Crie os metodos de pagamento desejados:

   * **Dinheiro**: um por POS (vinculado ao diario de caixa exclusivo)
   * **Cartao**: compartilhado, vinculado a um diario tipo "bank"
   * **Transferencia**: compartilhado, vinculado a outro diario tipo "bank"
   * **Conta Cliente**: compartilhado, sem diario, com ``split_transactions=True``
     (exige identificacao do cliente na venda POS)

7. **POS Config**

   Crie um POS para cada van em *Ponto de Venda > Configuracao > Pontos de Venda*.
   Configure os campos adicionais:

   * **E Van Config**: marcado
   * **Armazem**: armazem da van
   * **Load Picking Type**: tipo de carga da van
   * **Unload Picking Type**: tipo de descarga da van
   * **Driver Account**: conta a receber do motorista
   * **Van Transit Account**: conta de mercadoria em transito
   * **Cash Account**: conta de caixa
   * **Van Journal**: diario de fechamento
   * **Metodos de Pagamento**: dinheiro (exclusivo) + cartao, transferencia, etc.

8. **Motoristas**

   Cadastre os motoristas em *Van Sales > Motoristas* ou em Contatos com o campo
   "E Motorista Van" marcado.

9. **Estoque Inicial**

   Garanta que os produtos a serem vendidos tenham estoque disponivel no
   armazem principal (WH). O estoque sera transferido para a van via picking
   de carga.

Permissoes
~~~~~~~~~~

O modulo define dois grupos de acesso:

* **Van Sales / User**: acesso a sessoes, leitura de configuracoes
* **Van Sales / Manager**: pode fechar sessoes (action_post), reverter estados
  e acessar configuracoes
