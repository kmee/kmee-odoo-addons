Este módulo permite apontar a quantidade produzida em cada ordem de serviço
da ordem de produção, sem esperar a conclusão da ordem inteira.

- Cada ordem de serviço registra a quantidade produzida e o consumo
  proporcional dos seus componentes.
- Uma ordem só pode apontar até a quantidade já apontada pela ordem
  anterior e até o que os componentes reservados permitem produzir.
- A última ordem lança a quantidade apontada na ordem de produção. Se for
  menor que a planejada, o saldo segue em uma ordem de produção
  complementar (backorder).
- Um assistente corrige a quantidade apontada, respeitando as ordens vizinhas.
