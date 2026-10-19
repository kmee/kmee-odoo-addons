Ferramentas reutilizáveis, com pouca dependência do Odoo, para que HTML pesado
(e-mails, descrições longas) seja renderizado rápido sem perder o conteúdo
completo.

São utilitários em Python puro (sem ORM, testáveis isoladamente):

- `tools/html_sanitizer.py`: remove caracteres de largura zero, torna as imagens
  responsivas e com carregamento tardio, descarta blocos duplicados, reduz
  parágrafos vazios e gera um resumo limitado por caracteres visíveis.
- `tools/quote_detection.py`: classifica qual cenário de histórico citado o
  corpo contém (marcador do Odoo, Gmail, blockquote, divisor ou cabeçalhos do
  Outlook).
- `tools/quote_boundary.py`: `split_history(body)` devolve `(principal,
  histórico)`: a resposta mais recente e o histórico citado que vem depois.

O módulo não traz modelos nem telas próprias: é uma base para ser reutilizada
(por exemplo, por `mail_chatter_quote_summary`).
