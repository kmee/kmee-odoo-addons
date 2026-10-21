Otimiza o campo `description` dos tickets do `helpdesk_mgmt` (OCA):

- Sanitiza o HTML (caracteres de largura zero, estilos de imagem em in/cm,
  blocos duplicados, parágrafos vazios em sequência).
- Grava o HTML completo em `description_full` e deixa em `description` um
  resumo limitado por caracteres visíveis.
- Carrega o conteúdo completo sob demanda no formulário ("Ver conteúdo
  completo"), em blocos.
- Assistente para reprocessar as descrições já gravadas por `queue_job`.
