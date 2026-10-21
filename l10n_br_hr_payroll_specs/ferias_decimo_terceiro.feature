# language: pt
# encoding: utf-8

Funcionalidade: Férias e 13º Salário
  Como analista de DP da ABGF
  Quero gerenciar férias e 13º salário conforme a CLT e o Estatuto ABGF
  Para garantir o pagamento correto dos direitos dos funcionários

  Contexto:
    Dado que estou autenticado como analista de DP
    E os módulos "l10n_br_hr_vacation" e "l10n_br_hr_payroll" estão instalados

  # ─────────────────────────────────────────────
  # PERÍODO AQUISITIVO
  # ─────────────────────────────────────────────
  Esquema do Cenário: Dias de férias por faltas no período aquisitivo (CLT)
    Dado um funcionário com <faltas> faltas injustificadas no período aquisitivo
    Quando o período aquisitivo é completado
    Então o funcionário tem direito a <dias_ferias> dias de férias

    Exemplos:
      | faltas | dias_ferias | observacao                        |
      | 0      | 30          | Sem faltas: 30 dias (CLT art. 130)|
      | 5      | 30          | Até 5 faltas: 30 dias             |
      | 6      | 24          | 6 a 14 faltas: 24 dias            |
      | 14     | 24          | 6 a 14 faltas: 24 dias            |
      | 15     | 18          | 15 a 23 faltas: 18 dias           |
      | 23     | 18          | 15 a 23 faltas: 18 dias           |
      | 24     | 12          | 24 a 32 faltas: 12 dias           |
      | 32     | 12          | 24 a 32 faltas: 12 dias           |
      | 33     | 0           | Mais de 32 faltas: perde férias   |

  # ─────────────────────────────────────────────
  # CÁLCULO DO VALOR DAS FÉRIAS
  # ─────────────────────────────────────────────
  Cenário: Cálculo do valor de férias com adicional de 1/3
    Dado um funcionário CLT com salário de R$ 6.000,00
    Quando solicito férias de 30 dias
    Então o valor das férias é R$ 6.000,00
    E o adicional de 1/3 constitucional é R$ 2.000,00
    E o total bruto de férias é R$ 8.000,00
    E INSS é calculado sobre R$ 8.000,00
    E IRRF é calculado sobre R$ 8.000,00 (sem deduções mensais)

  Cenário: Abono pecuniário (venda de 1/3 das férias)
    Dado um funcionário CLT com salário de R$ 6.000,00
    E férias de 30 dias com abono pecuniário solicitado
    Quando processo o pagamento de férias
    Então os dias de férias gozadas são 20
    E o abono pecuniário é R$ 2.000,00 (10 dias × R$ 200,00/dia)
    E o total pago (antes de impostos) é R$ 10.666,67

  Esquema do Cenário: Férias fracionadas
    Dado um funcionário com 30 dias de férias disponíveis
    Quando solicito férias fracionadas em <parcelas> parcelas de <dias> dias
    Então o sistema <resultado>

    Exemplos:
      | parcelas | dias       | resultado                                       |
      | 2        | 15 e 15    | aceita — uma parcela deve ter mínimo 14 dias   |
      | 3        | 14, 8 e 8  | aceita — CLT permite 3 períodos desde 2017     |
      | 2        | 5 e 25     | rejeita — período mínimo é 14 dias consecutivos|
      | 4        | 8,8,7,7    | rejeita — máximo 3 períodos (Lei 13.467/2017)  |

  # ─────────────────────────────────────────────
  # FÉRIAS VENCIDAS
  # ─────────────────────────────────────────────
  Cenário: Alerta de férias vencidas
    Dado um funcionário com período concessivo vencendo em "30/06/2024"
    Quando a data atual é "01/05/2024"
    Então o sistema deve gerar alerta de "Férias a vencer em 60 dias"
    E notificar o gestor do funcionário

  Cenário: Dobro de férias por atraso do empregador
    Dado um funcionário cujo período concessivo venceu em "30/06/2024"
    E as férias não foram concedidas
    Quando a data atual é "01/07/2024"
    Então o sistema marca as férias como "Em Dobro"
    E o pagamento é calculado em dobro (CLT art. 137)

  # ─────────────────────────────────────────────
  # 13º SALÁRIO
  # ─────────────────────────────────────────────
  Cenário: Cálculo da 1ª parcela do 13º (adiantamento - novembro)
    Dado um funcionário CLT com salário de R$ 5.000,00
    E admitido em 01/01/2024 (12 avos completos)
    Quando processo a folha de adiantamento do 13º em novembro/2024
    Então a 1ª parcela do 13º é R$ 2.500,00 (50% do salário bruto)
    E não há desconto de INSS ou IRRF na 1ª parcela

  Esquema do Cenário: 13º proporcional por meses trabalhados
    Dado um funcionário admitido em <data_admissao> com salário de R$ 6.000,00
    Quando processo o 13º de 2024
    Então o 13º proporcional bruto é R$ <valor_13>

    Exemplos:
      | data_admissao | valor_13 | avos | descricao         |
      | 01/01/2024    | 6000.00  | 12   | 12/12 do salário  |
      | 01/07/2024    | 3000.00  | 6    | 6/12 do salário   |
      | 01/10/2024    | 1500.00  | 3    | 3/12 do salário   |
      | 16/12/2024    | 500.00   | 1    | 1/12 (15+ dias)   |
      | 25/12/2024    | 0.00     | 0    | Menos de 15 dias  |

  Cenário: Cálculo da 2ª parcela do 13º (dezembro)
    Dado um funcionário CLT com salário de R$ 5.000,00
    E 1ª parcela já paga de R$ 2.500,00
    Quando processo a 2ª parcela do 13º em dezembro/2024
    Então o 13º integral é R$ 5.000,00
    E o INSS do 13º é calculado sobre R$ 5.000,00
    E o IRRF do 13º é calculado sobre (5000 - INSS) separadamente do mês
    E o líquido da 2ª parcela = 5000 - INSS_13 - IRRF_13 - 2500 (já pago)

  Cenário: 13º na rescisão antes de novembro
    Dado um funcionário demitido sem justa causa em 30/09/2024
    E admitido em 01/01/2024 com salário de R$ 4.800,00
    Quando processo a rescisão
    Então o 13º proporcional é R$ 3.600,00 (9/12 × 4800)
    E INSS e IRRF do 13º são calculados e descontados na rescisão
