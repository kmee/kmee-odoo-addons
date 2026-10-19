# language: pt
# encoding: utf-8

Funcionalidade: Arquivos para o Governo (DIRF, RAIS, eSocial)
  Como responsável pelo compliance fiscal da ABGF
  Quero gerar os arquivos de obrigações acessórias corretamente
  Para evitar multas e garantir conformidade com a RFB, MTE e eSocial

  Contexto:
    Dado que estou autenticado como analista fiscal
    E o módulo "l10n_br_hr_arquivos_governo" está instalado
    E há pelo menos 12 meses de folha processada

  # ─────────────────────────────────────────────
  # DIRF
  # ─────────────────────────────────────────────
  Cenário: Geração da DIRF anual
    Dado que o ano-base é 2024
    Quando solicito a geração da DIRF
    Então o arquivo segue o layout atual da RFB
    E inclui todos os beneficiários com IRRF retido no ano
    E inclui beneficiários com renda total acima de R$ 28.559,70 (mesmo sem retenção)
    E o arquivo é gerado no formato .txt compatível com o programa da RFB

  Cenário: DIRF com 13º salário destacado
    Dado um funcionário com salário de R$ 8.000,00 ao longo de 2024
    E IRRF mensal retido de R$ 900,00/mês × 12 = R$ 10.800,00
    E IRRF sobre 13º de R$ 650,00
    Quando gero a DIRF de 2024
    Então o registro do funcionário mostra:
      | campo                     | valor       |
      | Rendimentos do Trabalho   | 96.000,00   |
      | IR Retido (mensal)        | 10.800,00   |
      | 13º Salário               | 8.000,00    |
      | IR Retido (13º)           | 650,00      |

  # ─────────────────────────────────────────────
  # RAIS
  # ─────────────────────────────────────────────
  Cenário: Geração da RAIS anual
    Dado que o ano-base é 2024
    Quando solicito a geração da RAIS
    Então o arquivo inclui todos os vínculos ativos e encerrados no ano
    E segue o layout do MTE (Ministério do Trabalho)
    E inclui dados de remunerações mensais, afastamentos e desligamentos

  Cenário: RAIS com funcionário afastado
    Dado um funcionário com afastamento por INSS de 01/03/2024 a 30/06/2024
    Quando gero a RAIS
    Então os meses de afastamento constam com remuneração zero
    E o motivo do afastamento é indicado corretamente

  # ─────────────────────────────────────────────
  # eSocial
  # ─────────────────────────────────────────────
  Cenário: Admissão - evento S-2200
    Dado um novo funcionário admitido em 01/04/2024
    Quando confirmo a admissão no sistema
    Então o sistema gera o evento eSocial "S-2200 - Cadastramento Inicial do Vínculo"
    E o XML segue o XSD vigente do eSocial
    E o evento é enviado antes do início das atividades do trabalhador
    E o sistema registra o protocolo de envio

  Cenário: Demissão - evento S-2299
    Dado um funcionário demitido em 30/06/2024
    Quando processo a rescisão contratual
    Então o sistema gera o evento eSocial "S-2299 - Desligamento"
    E inclui a data de desligamento, motivo e verbas rescisórias
    E o evento é enviado no prazo legal (até 10 dias após o desligamento)

  Cenário: Folha mensal - evento S-1200
    Dado que a folha de abril/2024 foi fechada e confirmada
    Quando envio a folha para o eSocial
    Então o sistema gera o evento "S-1200 - Remuneração do Trabalhador"
    E inclui todos os funcionários com suas bases e contribuições
    E o evento é enviado até o dia 15 do mês seguinte

  Cenário: Afastamento - evento S-2230
    Dado um funcionário com atestado médico de 5 dias
    Quando registro o afastamento no sistema
    Então se o afastamento for superior a 3 dias, gera o evento "S-2230 - Afastamento Temporário"
    E se for até 3 dias, apenas registra internamente sem envio ao eSocial

  # ─────────────────────────────────────────────
  # EFD-REINF
  # ─────────────────────────────────────────────
  Cenário: EFD-Reinf R-2010 para serviços prestados
    Dado que a ABGF contratou serviços com cessão de mão de obra no mês
    Quando processo a EFD-Reinf do mês
    Então o evento R-2010 é gerado com os valores retidos de INSS sobre serviços
    E o arquivo segue o layout atual do SPED/Reinf
