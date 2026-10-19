Recolhe o histórico de e-mail citado nas mensagens do chatter de qualquer
modelo. Cada mensagem mostra primeiro apenas a resposta mais recente e um botão
"Ler mais"; o histórico citado é buscado sob demanda, de modo que cadeias longas
de e-mail deixam de inflar a carga e o DOM do chatter.

Como funciona:

- O `body` gravado em `mail.message` **nunca é alterado**. Só o conteúdo enviado
  para a tela (`_message_format`) é resumido, e o histórico completo é entregue
  em partes pela chamada `load_quote_history_chunk`, lida do corpo original.
- A detecção e a separação entre resposta e histórico são determinísticas e
  feitas no servidor (reaproveitando o `html_optimizer`). O único código no
  navegador reage ao clique do usuário e não altera o DOM durante a renderização.
