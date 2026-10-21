# language: pt
# encoding: utf-8

Funcionalidade: Cálculo de Folha de Pagamento
  Como analista de DP da ABGF
  Quero que a folha de pagamento calcule corretamente todos os proventos e descontos
  Para garantir cumprimento das obrigações legais trabalhistas e previdenciárias

  Contexto:
    Dado que estou autenticado como analista de Departamento Pessoal
    E o módulo "l10n_br_hr_payroll" está instalado
    E as tabelas de INSS e IRRF de 2024 estão configuradas

  # ─────────────────────────────────────────────
  # INSS
  # ─────────────────────────────────────────────
  Esquema do Cenário: Cálculo do INSS com tabela progressiva 2024
    Dado um funcionário CLT com salário bruto de R$ <salario_bruto>
    Quando a folha do mês é calculada
    Então o desconto de INSS deve ser R$ <inss_esperado>

    Exemplos:
      | salario_bruto | inss_esperado | descricao                                        |
      | 1412.00       | 105.90        | Mínimo: 7.5% sobre toda a faixa (1412 * 7.5%)   |
      | 1500.00       | 112.50        | Faixa 1: 1412 * 7.5% + 88 * 9% = 105.90 + 7.92 |
      | 2666.68       | 208.49        | Teto da faixa 2                                  |
      | 3000.00       | 252.58        | Faixa 3: progressivo                             |
      | 4000.03       | 382.56        | Teto da faixa 3                                  |
      | 5000.00       | 531.15        | Faixa 4: progressivo                             |
      | 7786.02       | 908.86        | Teto do INSS 2024                                |
      | 10000.00      | 908.86        | Acima do teto: mantém R$ 908,86                  |
      | 20000.00      | 908.86        | Muito acima do teto: mantém R$ 908,86            |

  Cenário: INSS de servidor com regime RPPS não desconta INSS padrão
    Dado um funcionário estatutário com regime "RPPS"
    E salário de R$ 8.000,00
    Quando a folha é calculada
    Então não há desconto de INSS (RGPS)
    E há desconto de contribuição previdenciária RPPS conforme alíquota configurada

  # ─────────────────────────────────────────────
  # IRRF
  # ─────────────────────────────────────────────
  Esquema do Cenário: Cálculo do IRRF com tabela progressiva 2024
    Dado um funcionário CLT com salário bruto de R$ <salario_bruto>
    E sem dependentes
    Quando a folha do mês é calculada
    Então a base de cálculo do IRRF deve ser R$ <base_irrf>
    E o desconto de IRRF deve ser R$ <irrf_esperado>

    Exemplos:
      | salario_bruto | base_irrf | irrf_esperado | descricao                    |
      | 2259.20       | 2153.30   | 0.00          | Abaixo do limite de isenção  |
      | 3000.00       | 2847.42   | 44.12         | Faixa 2: 7.5%                |
      | 5000.00       | 4468.85   | 292.10        | Faixa 4: 22.5%               |
      | 10000.00      | 9091.14   | 1606.16       | Faixa 5: 27.5%               |

  Cenário: Dedução de dependentes no IRRF
    Dado um funcionário com salário bruto de R$ 5.000,00
    E INSS calculado de R$ 531,15
    Quando informo 2 dependentes para fins de IRRF
    Então a base do IRRF é reduzida em R$ 379,18 (2 × R$ 189,59)
    E o IRRF é recalculado sobre a base reduzida

  Cenário: Dedução de pensão alimentícia no IRRF
    Dado um funcionário com salário bruto de R$ 6.000,00
    E pensão alimentícia de R$ 1.200,00 (determinada judicialmente)
    Quando a folha é calculada
    Então a pensão é deduzida integralmente da base do IRRF
    E o valor é destacado no holerite como "Pensão Alimentícia"

  Cenário: IRRF zerado quando há isenção por moléstia grave
    Dado um funcionário com doença grave reconhecida (Lei 7.713/88)
    E salário de R$ 15.000,00
    Quando a folha é calculada
    Então o desconto de IRRF deve ser R$ 0,00
    E o holerite deve registrar o motivo "Isenção - Moléstia Grave"

  # ─────────────────────────────────────────────
  # FGTS
  # ─────────────────────────────────────────────
  Esquema do Cenário: Cálculo do FGTS
    Dado um funcionário "<tipo>" com salário de R$ <salario>
    Quando a folha é calculada
    Então o FGTS gerado é R$ <fgts_esperado>

    Exemplos:
      | tipo         | salario   | fgts_esperado | descricao         |
      | CLT          | 5000.00   | 400.00        | 8% sobre bruto    |
      | Aprendiz     | 1412.00   | 56.48         | 2% sobre bruto    |
      | Estatutário  | 8000.00   | 0.00          | RPPS, sem FGTS   |

  # ─────────────────────────────────────────────
  # CÁLCULO PROPORCIONAL
  # ─────────────────────────────────────────────
  Cenário: Folha proporcional por admissão no meio do mês
    Dado um funcionário com salário de R$ 6.000,00
    Quando é admitido no dia 16 de março de 2024 (31 dias no mês)
    Então o salário bruto proporcional é R$ 2.903,23 (16/31 × 6000)
    E INSS e IRRF são calculados sobre o valor proporcional
    E FGTS é calculado sobre o valor proporcional

  Cenário: Folha proporcional por demissão no meio do mês
    Dado um funcionário com salário de R$ 4.000,00
    Quando é demitido no dia 20 de março de 2024 (31 dias no mês)
    Então o salário bruto proporcional é R$ 2.580,65 (20/31 × 4000)

  Cenário: Folha com faltas não justificadas
    Dado um funcionário com salário de R$ 3.000,00 em fevereiro (29 dias em 2024)
    E o funcionário teve 2 faltas injustificadas
    Quando a folha é calculada
    Então o desconto de faltas é R$ 206,90 (2/29 × 3000)
    E o DSR é calculado proporcionalmente às faltas

  # ─────────────────────────────────────────────
  # FECHAMENTO
  # ─────────────────────────────────────────────
  Cenário: Processo completo de fechamento da folha
    Dado que estamos no mês de competência "03/2024"
    E há 150 funcionários ativos
    Quando inicio o processo de "Calcular Folha"
    Então o sistema processa todos os contracheques
    E exibe resumo com total de proventos, descontos e líquido
    E bloqueia alterações nos contracheques confirmados
    E gera os lançamentos contábeis automaticamente

  Cenário: Reprocessar folha antes do fechamento
    Dado uma folha em status "Rascunho"
    Quando altero dados de um funcionário (ex: nova falta)
    E clico em "Reprocessar"
    Então o contracheque é recalculado com os novos dados
    E o status volta para "Em Cálculo"

  Cenário: Não permitir fechar folha com inconsistências
    Dado uma folha com funcionário sem conta bancária informada
    Quando tento fechar a folha
    Então o sistema bloqueia o fechamento
    E lista todas as inconsistências encontradas
    E permite fechar somente após resolução
