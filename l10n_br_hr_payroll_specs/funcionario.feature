# language: pt
# encoding: utf-8

Funcionalidade: Cadastro de Funcionário Brasileiro
  Como responsável pelo RH da ABGF
  Quero cadastrar funcionários com todos os dados legais brasileiros
  Para garantir conformidade com a legislação trabalhista e previdenciária

  Contexto:
    Dado que estou autenticado como usuário de RH
    E o módulo "l10n_br_hr" está instalado

  # ─────────────────────────────────────────────
  # CPF
  # ─────────────────────────────────────────────
  Esquema do Cenário: Validação de CPF
    Dado um novo cadastro de funcionário
    Quando informo o CPF "<cpf>"
    Então o sistema deve "<resultado>"

    Exemplos:
      | cpf           | resultado                        |
      | 123.456.789-09 | aceitar o CPF como válido        |
      | 111.111.111-11 | rejeitar com erro de CPF inválido|
      | 000.000.000-00 | rejeitar com erro de CPF inválido|
      | 12345678900    | aceitar após formatar o CPF      |
      | 123.456.789-00 | rejeitar com erro de CPF inválido|

  Cenário: Cadastro completo com dados obrigatórios brasileiros
    Dado um novo funcionário chamado "João da Silva"
    Quando preencho os campos obrigatórios:
      | campo                    | valor            |
      | CPF                      | 123.456.789-09   |
      | PIS/PASEP                | 123.45678.90-1   |
      | Data de Admissão         | 01/03/2024       |
      | Tipo de Contrato         | CLT              |
      | Regime Previdenciário    | INSS             |
    Então o funcionário é salvo com sucesso
    E o número de matrícula é gerado automaticamente

  Cenário: Impedir duplicidade de CPF
    Dado que já existe um funcionário com CPF "123.456.789-09"
    Quando tento cadastrar outro funcionário com CPF "123.456.789-09"
    Então o sistema deve exibir erro "CPF já cadastrado para outro funcionário"

  Cenário: Impedir duplicidade de PIS/PASEP
    Dado que já existe um funcionário com PIS "123.45678.90-1"
    Quando tento cadastrar outro funcionário com PIS "123.45678.90-1"
    Então o sistema deve exibir erro "PIS/PASEP já cadastrado para outro funcionário"

  Cenário: Funcionário com deficiência
    Dado um funcionário cadastrado
    Quando marco o campo "Pessoa com Deficiência" como "Sim"
    E seleciono o tipo de deficiência "Física"
    Então o campo "CID" fica disponível para preenchimento
    E o sistema registra para fins de cota de PCD (Lei 8.213/91)

  # ─────────────────────────────────────────────
  # DADOS DE DOCUMENTOS
  # ─────────────────────────────────────────────
  Cenário: Registro de CTPS
    Dado um funcionário em processo de admissão
    Quando preencho os dados da CTPS:
      | campo          | valor   |
      | Número CTPS    | 123456  |
      | Série          | 0012    |
      | UF             | DF      |
      | Data Emissão   | 15/01/2010 |
    Então os dados são salvos e impressos no contrato de trabalho

  Cenário: Dados bancários para pagamento de salário
    Dado um funcionário ativo
    Quando informo a conta bancária:
      | campo     | valor       |
      | Banco     | Banco do Brasil |
      | Agência   | 1234-5      |
      | Conta     | 12345-6     |
      | Tipo      | Corrente    |
    Então a conta fica vinculada para geração da ordem de pagamento
