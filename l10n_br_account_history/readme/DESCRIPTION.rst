Históricos padrão para as partidas dos lançamentos contábeis, com template de
variáveis.

Em vez de cada rotina montar o próprio texto, o histórico vem de um template
como ``Pagamento ref. %{DOC} de %{PARCEIRO} em %{MM}/%{AAAA}``. As variáveis
disponíveis são de data (``%{DD}``, ``%{MM}``, ``%{AA}``, ``%{AAAA}``),
documento (``%{DOC}``), parceiro (``%{PARCEIRO}``), rótulo do campo de origem
(``%{CAMPO}``) e descrição da linha (``%{LINHA}``).

A substituição é literal, sem expressão nem condicional, de propósito:
histórico é texto de escrituração, não lugar de lógica.

Cada histórico pode carregar o **código no sistema contábil** do escritório,
usado pelos layouts de exportação que trabalham com código de histórico. O
mesmo texto alimenta os registros I200/I250 do SPED Contábil.

Este módulo define apenas o cadastro e a renderização; quem aplica o histórico
nas linhas são os módulos consumidores (templates contábeis, exportação).
