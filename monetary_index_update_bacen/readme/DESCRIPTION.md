Este módulo estende o *Monetary Index Update* para buscar e atualizar
automaticamente os índices brasileiros publicados no Sistema Gerenciador
de Séries Temporais (SGS) do Banco Central do Brasil (BCB).

Já vem com SELIC (série 4390), IPCA (433), INPC (188) e IGP-M (189).
Qualquer outro índice passa a ser atualizado ao preencher o código da
série do SGS no cadastro do índice.

Inclui o provedor que consome a API do BCB, um assistente para carga
manual de um período e um cron diário que busca de novo os últimos três
meses de cada índice (as séries mensais saem por volta do dia 10 do mês
seguinte e podem ser revistas).

Substitui o módulo *monetary_index_update_selic*. Em banco que tinha o
módulo antigo instalado, atualizar o *monetary_index_update* renomeia o
módulo e mantém os registros.
