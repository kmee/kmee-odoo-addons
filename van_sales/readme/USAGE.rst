Fluxo operacional
~~~~~~~~~~~~~~~~~

O ciclo de vida de uma sessao van segue 6 estados em sequencia:

::

    Rascunho → Em Carregamento → Carregado → Em Rota → Retornado → Fechado

1. Criar Sessao (Rascunho)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Acesse *Van Sales > Sessoes > Nova* e preencha:

* **Motorista**: selecione o motorista responsavel
* **POS Config**: selecione o POS do caminhao

A lista de precos sera preenchida automaticamente a partir do POS.

2. Iniciar Carregamento
^^^^^^^^^^^^^^^^^^^^^^^^

Clique em **Iniciar Carregamento**. O sistema:

* Carrega automaticamente as linhas com produtos que ja estao na van
  (estoque residual de sessoes anteriores)
* Preenche ``qty_initial`` (quantidade atual na van) e ``qty_demand``
  (quantidade desejada para a viagem)

Ajuste as quantidades conforme necessario e adicione novos produtos.

3. Confirmar Carga
^^^^^^^^^^^^^^^^^^^

Clique em **Gerar Picking de Carga**. O sistema:

* Cria um picking interno (armazem WH → van) com as quantidades adicionais
  (``qty_demand - qty_initial``) para cada produto
* Se toda a quantidade ja estiver na van, pula direto para "Carregado"

O picking deve ser validado pelo armazem. Ao validar, o estado muda
automaticamente para **Carregado**.

4. Abrir POS (Em Rota)
^^^^^^^^^^^^^^^^^^^^^^^^

Com a sessao em "Carregado", clique em **Abrir POS**. O sistema:

* Abre a interface POS padrão do Odoo
* Vincula a sessao POS a sessao van
* Muda o estado para **Em Rota**

O motorista realiza vendas normalmente no POS, podendo usar qualquer
metodo de pagamento configurado (dinheiro, cartao, transferencia, conta
cliente).

5. Fechar POS (Retornado)
^^^^^^^^^^^^^^^^^^^^^^^^^^

Ao fechar o POS (fim do dia / retorno), o sistema automaticamente:

* Captura todas as vendas e devolucoes POS
* Calcula ``qty_sold`` e ``qty_devolution`` por produto
* Registra a diferenca de caixa (``cash_diff``) a partir do POS
* Cria o picking de descarga (van → armazem WH) com as quantidades
  esperadas de retorno
* Muda o estado para **Retornado**

O conferente do armazem deve validar o picking de descarga, informando
as quantidades reais recebidas. Diferencas geram ``qty_diff`` nas linhas.

6. Fechar Sessao
^^^^^^^^^^^^^^^^^

Com o picking de descarga validado, o gestor clica em **Postar Fechamento**:

* Gera um lancamento contabil (``account.move``) com:

  - **Diferenca de estoque**: debita motorista, credita mercadoria em transito
  - **Diferenca de caixa**: debita motorista (falta) ou credita motorista (sobra)

* Se nao houver diferencas, fecha a sessao sem lancamento
* Estado muda para **Fechado**

Campos calculados por linha
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cada linha (``van.session.line``) possui campos computados:

* ``qty_initial``: estoque ja presente na van antes da carga
* ``qty_demand``: quantidade desejada para carregar
* ``qty_loaded``: quantidade efetivamente carregada (do picking)
* ``qty_out``: total de saida = ``qty_initial + qty_loaded``
* ``qty_sold``: quantidade vendida pelo POS
* ``qty_devolution``: quantidade devolvida pelo cliente via POS
* ``qty_returned``: quantidade retornada ao armazem (do picking de descarga)
* ``qty_scrap``: quantidade descartada (via stock.scrap no picking)
* ``qty_diff``: diferenca = ``qty_out - qty_sold + qty_devolution - qty_returned - qty_scrap``
* ``price_unit``: preco unitario (da pricelist)
* ``amount``: valor da diferenca = ``qty_diff * price_unit``

Abono de diferencas
~~~~~~~~~~~~~~~~~~~

Linhas com diferenca podem ser abonadas marcando o campo ``waived`` e
preenchendo ``waive_reason`` com justificativa de pelo menos 20 caracteres.
Linhas abonadas nao geram lancamento contabil.

Reversao de estados
~~~~~~~~~~~~~~~~~~~

Em caso de erro, o gestor (grupo Manager) pode:

* **Voltar ao Rascunho**: a partir de "Em Carregamento" ou "Carregado"
  (cancela o picking de carga)
* **Voltar a Carregado**: a partir de "Retornado"
  (cancela o picking de descarga e limpa links de venda)

Relatorios
~~~~~~~~~~

O modulo inclui 4 relatorios pre-configurados em *Van Sales > Relatorios*:

* **Analise de Vendas**: pivot/graph geral com vendas, diferencas e valores
* **Desempenho por Motorista**: agrupado por motorista com metricas-chave
* **Movimentacao de Produtos**: analise por produto com sell-through rate
* **Controle de Diferencas**: somente linhas com diferenca, agrupadas por motorista

Todos baseados na view SQL ``report.van.session.line`` com filtros por periodo,
estado e agrupamentos configuráveis.

Impressoes
~~~~~~~~~~

* **Ticket de Carga**: relatorio de impressao das linhas de carregamento
  (disponivel na sessao em estado "Carregado")
* **Resumo da Sessao**: relatorio completo de fechamento com totais,
  diferencas e pagamentos

Estoque residual (carry-over)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Produtos nao vendidos e nao retornados ao armazem permanecem no estoque
da van. Na proxima sessao, ao clicar "Iniciar Carregamento", esses
produtos sao automaticamente carregados com ``qty_initial`` preenchida,
e ``qty_demand`` ajustada para incluir a quantidade ja presente.
