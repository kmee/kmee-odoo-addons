# language: pt
# encoding: utf-8

Funcionalidade: Verbas Salariais e Benefícios
  Como analista de DP da ABGF
  Quero que adicionais e benefícios sejam calculados corretamente
  Para garantir o pagamento justo e legal

  Contexto:
    Dado que estou autenticado como analista de DP
    E os módulos "l10n_br_hr_allowance" e "l10n_br_hr_benefit" estão instalados

  # ─────────────────────────────────────────────
  # HORA EXTRA
  # ─────────────────────────────────────────────
  Esquema do Cenário: Cálculo de hora extra
    Dado um funcionário com salário de R$ 3.000,00 e jornada de 220h mensais
    E realizou <horas_extras> horas extras em <tipo>
    Quando a folha é calculada
    Então o valor das horas extras é R$ <valor_esperado>

    Exemplos:
      | horas_extras | tipo              | valor_esperado | descricao                      |
      | 10           | dias úteis        | 204.55         | 10 × (3000/220) × 1.50         |
      | 5            | domingos/feriados | 136.36         | 5 × (3000/220) × 2.00          |
      | 10           | noturnas úteis    | 224.61         | adicional noturno + HE         |

  # ─────────────────────────────────────────────
  # ADICIONAL NOTURNO
  # ─────────────────────────────────────────────
  Cenário: Adicional noturno (22h às 5h)
    Dado um funcionário com salário de R$ 3.000,00
    E que trabalha das 22h às 06h (8 horas noturnas)
    Quando a folha é calculada
    Então o adicional noturno é 20% sobre as horas de 22h às 05h
    E cada hora noturna é computada como 52min30s (hora reduzida)

  # ─────────────────────────────────────────────
  # ADICIONAIS DE RISCO
  # ─────────────────────────────────────────────
  Esquema do Cenário: Adicional de periculosidade e insalubridade
    Dado um funcionário com salário de R$ <salario>
    E exposto a agente "<agente>" com grau "<grau>"
    Quando a folha é calculada
    Então o adicional é R$ <adicional>

    Exemplos:
      | salario | agente           | grau  | adicional | base_calculo                    |
      | 5000.00 | Eletricidade     | —     | 600.00    | 30% do salário (periculosidade) |
      | 5000.00 | Ruído            | Médio | 169.44    | 20% do salário mínimo           |
      | 5000.00 | Produtos Químicos| Máximo| 338.88   | 40% do salário mínimo           |
      | 5000.00 | Calor            | Mínimo| 84.72    | 10% do salário mínimo           |

  Cenário: Periculosidade e insalubridade não são acumuláveis
    Dado um funcionário exposto a periculosidade E insalubridade
    Quando configuro os dois adicionais
    Então o sistema exibe aviso "Adicionais não acumuláveis — escolha o mais favorável ao trabalhador"
    E permite selecionar qual aplicar

  # ─────────────────────────────────────────────
  # SALÁRIO FAMÍLIA
  # ─────────────────────────────────────────────
  Esquema do Cenário: Salário família por filhos
    Dado um funcionário com salário de R$ <salario>
    E <filhos> filhos com até 14 anos
    Quando a folha é calculada
    Então o salário família é R$ <valor>

    Exemplos:
      | salario | filhos | valor  | descricao                          |
      | 1412.00 | 1      | 62.04  | Faixa 1: até R$1.869,34 → R$62,04  |
      | 1800.00 | 2      | 124.08 | Faixa 1: 2 × R$ 62,04             |
      | 1900.00 | 1      | 43.84  | Faixa 2: até R$2.903,98 → R$43,84  |
      | 3000.00 | 3      | 0.00   | Acima do teto: sem salário família |

  # ─────────────────────────────────────────────
  # BENEFÍCIOS
  # ─────────────────────────────────────────────
  Cenário: Vale-Refeição não incide INSS ou IRRF
    Dado um funcionário com Vale-Refeição de R$ 800,00/mês
    Quando a folha é calculada
    Então o VR não compõe a base de cálculo do INSS
    E o VR não compõe a base de cálculo do IRRF
    E aparece como "Benefício Não Tributável" no holerite

  Cenário: Desconto de plano de saúde coparticipação
    Dado um funcionário com plano de saúde com coparticipação de R$ 150,00
    Quando a folha é calculada
    Então R$ 150,00 é descontado como "Plano de Saúde - Coparticipação"
    E o desconto reduz a base do IRRF (benefício dedutível)

  Cenário: Vale-Transporte com desconto máximo legal
    Dado um funcionário com salário de R$ 2.000,00
    E VT de R$ 200,00/mês
    Quando a folha é calculada
    Então o desconto de VT é R$ 60,00 (máximo 6% do salário = 120,00, mas o VT é R$200)
    E o empregador custeia R$ 140,00 (diferença)

  Cenário: Vale-Transporte com valor menor que 6% do salário
    Dado um funcionário com salário de R$ 5.000,00
    E VT de R$ 100,00/mês
    Quando a folha é calculada
    Então o desconto de VT é R$ 100,00 (6% = R$300, mas VT é só R$100)
