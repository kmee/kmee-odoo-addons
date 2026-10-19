Este é um módulo base que fornece a infraestrutura para atualizar valores monetários utilizando índices econômicos, como SELIC, IPCA, INPC, entre outros. Ele deve ser estendido por outros módulos que implementarão a funcionalidade específica para diferentes partes do sistema (vendas, contratos, faturas, etc.).

O módulo permite cadastrar e gerenciar índices monetários com suas respectivas taxas históricas, associadas a autoridades emissoras (como BACEN, IBGE) e países específicos. Também fornece um serviço de cálculo de correção monetária que pode ser utilizado por módulos dependentes.

Módulos que estendem este módulo base podem aplicar correções monetárias em campos específicos de seus modelos, selecionando o índice desejado e o período de atualização (data inicial e final), com prévia visualização dos valores atualizados antes da confirmação.
