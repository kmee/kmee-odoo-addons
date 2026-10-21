# Help Desk Ticket Stage Duration

Este módulo melhora o sistema de helpdesk para rastrear e exibir a duração que cada
ticket passa em cada estágio.

## Funcionalidades

### Melhorias na Exibição de Duração

A exibição de duração foi completamente reformulada para mostrar:

- **Semanas** (semana/semanas)
- **Dias** (dia/dias)
- **Horas** (hora/horas)
- **Minutos** (minuto/minutos)
- **Segundos** (segundo/segundos)

### Exemplos de Exibição

- `2 semanas, 3 dias, 5 horas, 30 minutos`
- `1 dia, 12 horas, 45 minutos, 30 segundos`
- `3 horas, 15 minutos (em andamento)`

### Características

1. **Dados Salvos em Segundos**: A duração é armazenada como valor numérico em segundos
   no campo `duration_seconds`
2. **Exibição Formatada**: O campo `duration_display` mostra a duração em formato
   humanizado (char)
3. **Duração em Tempo Real**: Para tickets ainda em andamento, a duração é calculada em
   tempo real
4. **Formato Humanizado**: A duração é exibida em português com pluralização correta
5. **Granularidade Configurável**: Por padrão mostra até 4 unidades de tempo (ex:
   semanas, dias, horas, minutos)
6. **Tempo no Estágio Atual**: Campos computados para mostrar o tempo no estágio atual
   (útil para kanban)

### Novas Views

- **View de Lista**: Lista todas as durações de estágio com filtros
- **View Kanban Melhorada**: Mostra o tempo no estágio atual nos cards
- **View de Lista de Tickets**: Inclui coluna com tempo no estágio atual
- **Filtros**:
  - "In Progress" - durações ainda em andamento
  - "Completed" - durações finalizadas
- **Agrupamento**: Por estágio ou por ticket

### Campos Adicionados

#### Para Stage Duration (`helpdesk.ticket.stage.duration`)

- `duration_seconds`: Duração em segundos (campo Float para cálculos e armazenamento)
- `duration_display`: Duração formatada para exibição (campo Char)

#### Para Ticket (`helpdesk.ticket`)

- `current_stage_duration_seconds`: Tempo no estágio atual em segundos (campo Float)
- `current_stage_duration_display`: Tempo no estágio atual formatado (campo Char)

### Estrutura dos Dados

```python
# Exemplo de dados armazenados:
duration_seconds = 1296000.0  # 2 semanas, 1 dia, 12 horas em segundos
duration_display = "2 semanas, 1 dia, 12 horas"  # Exibição formatada

# Para o estágio atual:
current_stage_duration_seconds = 3600.0  # 1 hora em segundos
current_stage_duration_display = "1 hora (atual)"  # Exibição formatada
```

## Instalação

1. Instale o módulo `helpdesk_mgmt_ticket_life_cycle`
2. Acesse um ticket do helpdesk
3. Vá para a aba "Stage Durations" para ver as durações
4. Use o menu "Stage Durations" para ver todas as durações
5. No kanban, veja o tempo no estágio atual em cada card

## Uso

O módulo funciona automaticamente:

- Quando um ticket é criado, inicia o rastreamento do primeiro estágio
- Quando o estágio é alterado, finaliza o rastreamento do estágio anterior e inicia o
  novo
- A duração é calculada automaticamente e salva em segundos
- A exibição é formatada automaticamente em formato humanizado
- O tempo no estágio atual é atualizado em tempo real

## Vantagens da Implementação

1. **Performance**: Dados numéricos são mais eficientes para cálculos e consultas
2. **Flexibilidade**: O campo em segundos permite cálculos matemáticos precisos
3. **Usabilidade**: A exibição formatada é amigável ao usuário
4. **Relatórios**: Fácil criação de relatórios usando o campo numérico
5. **Kanban**: Visualização rápida do tempo no estágio atual nos cards
6. **Tempo Real**: Atualização automática do tempo em andamento
