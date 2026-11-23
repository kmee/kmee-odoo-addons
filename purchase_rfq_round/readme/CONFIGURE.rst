**Requisição gerada pelo planejamento.** Instale ``ddmrp_purchase_request`` e
marque "Purchase Request" nos produtos comprados com buffer: o botão de
reposição do buffer passa a criar requisições de compra.

**Alçadas (com os módulos OCA ``purchase_request_tier_validation`` e
``purchase_tier_validation``).** Em Configurações > Técnico > Tier Validation >
Tier Definition:

* Requisição (``purchase.request``): uma regra por faixa de valor estimado,
  com o aprovador do planejamento (ex.: até R$ 50 mil, coordenador; acima,
  gerente). A rodada só aceita linhas de requisição aprovadas.
* Pedido (``purchase.order``): regras por valor total (``amount_total``) e, se
  preciso, por categoria de produto. As cotações vencedoras de uma rodada
  fechada seguem essa aprovação antes de virar pedido.

**Fila.** Com rodadas grandes, as cotações são criadas por ``queue_job``: o
servidor precisa do ``queue_job`` carregado (``server_wide_modules``) e do canal
de fila configurado. O limite de linhas para usar a fila fica no parâmetro
``purchase_rfq_round.job_threshold``.
