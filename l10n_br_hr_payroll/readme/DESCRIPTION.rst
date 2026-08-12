Folha de Pagamento Brasileira para Odoo 16.0.

Implementa os cálculos de:

* INSS (tabela progressiva por vigência)
* IRRF (tabela progressiva por vigência, desconto simplificado e redutor)
* FGTS (8% CLT, 2% aprendiz)
* Hora extra 50% e 100%
* Adicional noturno (20%)
* Adicional de periculosidade (30%)
* Adicional de insalubridade (10%, 20%, 40% do salário mínimo)
* Salário família
* Faltas injustificadas e DSR
* Estruturas CLT e Estatutário

Encargos patronais por regime tributário
----------------------------------------

O custo do empregador é calculado a partir do regime tributário da empresa
(``tax_framework`` do ``l10n_br_fiscal``) e dos parâmetros de folha cadastrados
na empresa (aba **Encargos da Folha**): RAT, FAP, código FPAS e alíquota de
terceiros da lotação padrão, anexo do Simples Nacional e opção pela CPRB.

Rubricas patronais (categoria COMP, informativas: são custo, não descontam do
empregado e não entram no líquido):

* **CPP** - contribuição previdenciária patronal de 20% (Lei 8.212/91, art. 22, I)
* **RAT** - RAT ajustado, isto é, RAT x FAP (art. 22, II; Decreto 3.048/99, art. 202-A)
* **TERCEIROS** - outras entidades e fundos, pela alíquota do código FPAS
  (indústria, FPAS 507: 5,8%)

Variação por regime:

* **Lucro Real / Presumido**: encargo cheio (CPP + RAT + terceiros)
* **Simples Nacional, anexos I, II, III e V**: nenhuma das três é devida (CPP e
  RAT no DAS pela LC 123/2006, art. 13, VI; terceiros dispensados pelo §3º);
  permanece apenas o FGTS
* **Simples Nacional, anexo IV**: CPP e RAT por fora do DAS (art. 18, §5º-C),
  sem terceiros. O anexo pode ser declarado no CONTRATO quando a atividade do
  empregado difere da atividade preponderante da empresa
* **CPRB (desoneração em transição)**: a CPP é reduzida pela proporção do ano
  (Lei 14.973/2024: 25% em 2025, 50% em 2026, 75% em 2027, extinção em 2028),
  parametrizada por vigência em *Tabelas Fiscais BR > Transição da CPRB*. RAT e
  terceiros permanecem INTEGRAIS, e a gratificação natalina tem coluna própria
  (sem CPP de 2025 a 2027)

Provisões trabalhistas
----------------------

Rubricas de provisão mensal (categoria PROV, também fora do líquido), para que
o custo seja reconhecido por competência (CPC 33; dedutibilidade nos arts. 342
e 343 do RIR/2018):

* **PROV_FERIAS** - 1/12 da remuneração com o 1/3 constitucional
* **PROV_FERIAS_ENC** - encargos patronais sobre a provisão de férias, excluída
  a parcela que se espera pagar como verba indenizatória (férias indenizadas
  não têm INSS nem FGTS)
* **PROV_13** - 1/12 da remuneração
* **PROV_13_ENC** - encargos sobre a provisão do 13º (no optante da CPRB, sem
  CPP até 2027)

Conferência (salário de R$ 6.000,00, competência 2026, FAP 1,0):

======================  =========  =========  =========  =========
Regime                  CPP        RAT        Terceiros  FGTS
======================  =========  =========  =========  =========
Lucro Real (RAT 3%)      1.200,00     180,00     348,00     480,00
Lucro Presumido (2%)     1.200,00     120,00     348,00     480,00
CPRB 2026 (RAT 3%)         600,00     180,00     348,00     480,00
Simples anexo III            0,00       0,00       0,00     480,00
Simples anexo IV (2%)    1.200,00     120,00       0,00     480,00
======================  =========  =========  =========  =========
