# Guia Funcional para Suporte Odoo

## Módulo

`helpdesk_description_optimizer`

## Objetivo do módulo

Este módulo melhora a abertura e a visualização de chamados do Helpdesk quando a
descrição do ticket está muito grande, especialmente em casos de:

- tickets criados a partir de e-mails longos
- tickets com muitas imagens
- tickets com assinaturas, rodapés e conteúdo repetido
- tickets com histórico de conversa muito pesado

Na prática, o módulo tenta deixar o campo de descrição mais leve para o Odoo carregar
melhor a tela do chamado.

## O que o módulo faz

Quando um ticket é criado ou atualizado com uma descrição grande:

- o sistema limpa e organiza o HTML da descrição
- mantém uma versão resumida no campo principal de descrição
- guarda o conteúdo completo em um campo interno chamado `description_full`
- mostra o conteúdo completo somente quando necessário

## Benefício esperado

Os principais ganhos esperados são:

- abertura mais rápida de tickets pesados
- menos travamentos na tela do chamado
- menos lentidão ao renderizar HTML grande
- preservação do conteúdo completo quando ele for necessário

## Como isso aparece para o usuário

Na tela do ticket, o usuário normalmente verá:

- uma descrição mais curta e leve
- um botão para carregar ou expandir o conteúdo completo, quando existir

Se o ticket for curto, esse botão pode não aparecer. Isso é esperado.

## Quando o botão de conteúdo completo aparece

O botão aparece quando o sistema identifica que existe conteúdo adicional guardado no
campo completo da descrição.

Em geral isso acontece quando:

- o ticket tem HTML muito grande
- o ticket veio de e-mail com muito conteúdo
- houve redução do texto exibido para melhorar performance

## O que é o reprocessamento

O reprocessamento serve para aplicar essa otimização em tickets antigos, que já existiam
antes do módulo ou antes de alguma melhoria na regra de sanitização.

Ele não é voltado para uso diário. É uma ferramenta administrativa.

## Onde acessar o reprocessamento

No ambiente atual, o caminho esperado é:

`Helpdesk > Configurações > Reprocessar Descrições (Helpdesk)`

## Quem deve usar o reprocessamento

Somente usuários com perfil administrativo e autorização para configuração do sistema.

## O que acontece ao iniciar o reprocessamento

Ao clicar em `Iniciar Reprocessamento`:

- o Odoo cria um job em segundo plano
- o processamento acontece de forma assíncrona
- a tela do usuário não deve ficar travada
- o sistema percorre os tickets com descrição preenchida
- atualiza os tickets que precisam de otimização

## Comportamento esperado do job

Durante a execução:

- o wizard pode ficar em estado `Processando`
- a conclusão pode demorar, dependendo da quantidade de tickets
- em bases grandes, isso pode levar vários minutos

Ao concluir:

- o status deve mudar para `Concluído`
- a tela pode mostrar quantidade de tickets processados
- a tela pode mostrar quantidade de tickets atualizados

## Situações em que o suporte pode usar esse recurso

O suporte pode considerar o reprocessamento quando houver relatos como:

- tickets antigos demoram muito para abrir
- descrições antigas ficaram muito pesadas
- chamados importados de e-mail estão lentos
- foi feita atualização do módulo e é necessário aplicar a melhoria no legado

## O que o suporte deve verificar antes de abrir incidente técnico

### 1. Confirmar se o problema acontece em tickets antigos ou novos

Se o problema ocorre só em tickets antigos, pode ser caso de reprocessamento.

### 2. Confirmar se o botão de carregar conteúdo completo aparece

Se aparece, o módulo provavelmente está ativo.

### 3. Confirmar se o job foi criado

Em modo desenvolvedor ou com apoio técnico, verificar a fila de jobs do Odoo.

### 4. Confirmar se o job concluiu

Se o job ficou parado em `pending`, `enqueued`, `started` ou `failed`, o suporte deve
registrar isso no chamado técnico.

## Sinais de funcionamento correto

Indícios de que o módulo está funcionando:

- tickets grandes abrem com mais rapidez
- existe botão para expandir descrição em chamados pesados
- o reprocessamento cria job em segundo plano
- o job conclui sem erro

## Sinais de problema

Indícios comuns de problema:

- ticket grande continua travando a tela
- botão de expandir não aparece em chamados claramente pesados
- wizard fica eternamente em `Processando`
- job falha na fila
- erro relacionado a `queue_job`
- erro ao abrir o conteúdo completo do ticket

## Perguntas comuns do suporte

### O módulo apaga informação da descrição?

Não deve apagar a informação útil do ticket. A proposta é resumir a exibição principal e
preservar o conteúdo completo em campo interno.

### O usuário final perde acesso ao conteúdo original?

Não deveria perder. O conteúdo completo deve continuar disponível sob demanda.

### Todo ticket passa por otimização?

Nem sempre. Tickets curtos podem permanecer sem diferença perceptível.

### É normal o reprocessamento demorar?

Sim. Em bases grandes, é esperado.

### É normal não haver mudança visual em alguns tickets?

Sim. Se o ticket já era curto ou já estava adequado, a mudança pode ser mínima.

## Limites conhecidos

Este módulo melhora performance de descrição, mas não resolve sozinho outros problemas
de lentidão do Odoo, como:

- infraestrutura lenta
- excesso de carga no servidor
- problemas gerais de banco de dados
- anexos externos indisponíveis
- erros de fila de jobs

## Procedimento de triagem para suporte

### Cenário 1: ticket abre lentamente

Verificar:

- se a descrição do ticket é muito grande
- se há muitas imagens ou histórico de e-mail
- se o botão de conteúdo completo aparece

Se o problema for em ticket antigo:

- considerar uso do reprocessamento

### Cenário 2: reprocessamento não conclui

Verificar:

- se o job runner está ativo
- se existe job criado
- se o job está em `failed`
- se existe mensagem de erro na fila

Se houver falha:

- encaminhar para equipe técnica com print, horário e identificação do job

### Cenário 3: usuário diz que parte do conteúdo sumiu

Verificar:

- se existe botão para carregar conteúdo completo
- se o ticket foi reprocessado
- se o conteúdo completo é carregado ao expandir

## Informações úteis para abrir chamado técnico

Quando o suporte escalar para desenvolvimento, enviar:

- ID do ticket com problema
- horário aproximado do erro
- nome do usuário afetado
- print da tela
- status do wizard, se houver
- status do job na fila, se houver
- mensagem de erro copiada exatamente como apareceu

## Resumo para o suporte

Este módulo existe para deixar tickets pesados mais leves no Helpdesk, sem perder o
conteúdo completo. O uso mais sensível para suporte é o reprocessamento, que deve ser
entendido como uma rotina administrativa em segundo plano. Quando houver erro, o ponto
principal de verificação é a fila de jobs.
