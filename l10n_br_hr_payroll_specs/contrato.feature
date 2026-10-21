# language: pt
# encoding: utf-8

Funcionalidade: Gestão de Contratos de Trabalho
  Como gestor de RH da ABGF
  Quero gerenciar contratos de trabalho com tipos e regimes corretos
  Para calcular corretamente encargos e benefícios de cada tipo de vínculo

  Contexto:
    Dado que estou autenticado como usuário de RH
    E o módulo "l10n_br_hr_contract" está instalado

  # ─────────────────────────────────────────────
  # TIPOS DE CONTRATO
  # ─────────────────────────────────────────────
  Esquema do Cenário: Criar contrato por tipo de vínculo
    Dado um funcionário ativo "<funcionario>"
    Quando crio um contrato com tipo "<tipo_contrato>"
    E salário de R$ <salario>
    Então a estrutura salarial "<estrutura>" é aplicada automaticamente
    E o regime previdenciário "<regime>" é configurado

    Exemplos:
      | funcionario  | tipo_contrato   | salario   | estrutura          | regime    |
      | Funcionário A | CLT            | 5000.00   | CLT                | INSS      |
      | Funcionário B | Estatutário    | 8000.00   | ESTATUTO_ABGF      | RPPS      |
      | Funcionário C | CLT - Aprendiz | 1412.00   | APRENDIZ           | INSS      |
      | Funcionário D | Contrato Temp  | 3000.00   | CLT_TEMPORARIO     | INSS      |

  # ─────────────────────────────────────────────
  # VIGÊNCIA
  # ─────────────────────────────────────────────
  Cenário: Contrato com prazo determinado
    Dado um funcionário com contrato a prazo indeterminado
    Quando altero o contrato para prazo determinado com término em "31/12/2024"
    Então o sistema alerta quando a data de término se aproxima (30 dias antes)
    E bloqueia renovação automática se não houver ação do RH

  Cenário: Histórico de alterações salariais
    Dado um funcionário com salário de R$ 3.000,00
    Quando registro um aumento para R$ 3.500,00 a partir de "01/04/2024"
    Então o contrato anterior é encerrado em "31/03/2024"
    E um novo contrato é criado a partir de "01/04/2024" com R$ 3.500,00
    E o histórico salarial fica disponível para consulta

  Cenário: Contrato não pode ter salário abaixo do mínimo
    Dado um funcionário em processo de contratação
    Quando informo salário de R$ 1.000,00
    Então o sistema exibe aviso "Salário abaixo do mínimo vigente (R$ 1.412,00)"
    E impede salvar se o tipo de contrato for "CLT"

  # ─────────────────────────────────────────────
  # JORNADA
  # ─────────────────────────────────────────────
  Cenário: Configurar jornada de trabalho
    Dado um contrato CLT
    Quando configuro a jornada:
      | campo                | valor       |
      | Horas por semana     | 40          |
      | Dias por semana      | 5           |
      | Horário padrão       | 08:00-17:00 |
      | Intervalo intrajornada | 1 hora   |
    Então o sistema calcula o salário-hora corretamente
    E o adicional de hora extra fica configurado em 50% (normal) e 100% (domingo/feriado)

  Cenário: Afastamento não encerra contrato
    Dado um funcionário com contrato ativo
    Quando registro um afastamento por "INSS - Auxílio-Doença" a partir de "01/05/2024"
    Então o contrato permanece ativo
    E a folha do mês é calculada proporcionalmente (dias trabalhados antes do afastamento)
    E os meses de INSS não contam para férias durante o afastamento
