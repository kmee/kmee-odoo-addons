Acelera o formulário de tickets com `description` pesada (cadeias longas de
e-mail, muitas imagens, assinaturas repetidas) em `helpdesk.ticket` (módulo
`helpdesk_mgmt` da OCA), sem nunca alterar a descrição gravada.

Como funciona:

- O campo `description` continua sendo a fonte completa e intacta, então nada se
  perde ao editar, duplicar ou reprocessar.
- O campo derivado e armazenado `description_summary` guarda uma prévia otimizada
  e de tamanho limitado (imagens responsivas e com carregamento tardio, remoção
  de caracteres de largura zero e de blocos duplicados, redução de parágrafos
  vazios). É recalculado sempre que a descrição muda.
- O formulário usa o widget `description_optimizer`: em leitura mostra o resumo
  com um botão de "Ler mais" / "Ler menos" que revela a descrição completa; em
  edição, edita a descrição completa normalmente.

É a versão comunitária do otimizador de descrição da AG; atua sobre o
`helpdesk_mgmt` (não sobre o módulo `helpdesk` Enterprise).
