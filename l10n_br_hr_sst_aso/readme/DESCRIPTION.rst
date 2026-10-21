Exames ocupacionais (ASO) e PCMSO da NR-7, sobre o exame médico da OCA.

O ``hr_employee_medical_examination`` entrega o exame com estados, chatter e
geração em massa. Este módulo acrescenta o que a NR-7 e o evento S-2220 exigem:

* **PCMSO** por empresa e estabelecimento, com médico coordenador, vigência,
  periodicidade padrão, periodicidade por faixa etária ou por exposição a risco
  e campo do relatório analítico anual.
* **Campos do ASO**: tipo de exame (admissional, periódico, retorno, mudança de
  risco ocupacional, pontual e demissional), médico emitente com CRM e UF,
  clínica, resultado apto ou inapto, restrição funcional, vencimento e
  **exames complementares** com procedimento da Tabela 27.
* **Agendamento automático** do exame periódico a partir do vencimento do ASO
  anterior, e geração do exame de retorno ao trabalho para afastamento acima de
  30 dias.
* **Bloqueio ou alerta** na abertura do contrato sem o ASO admissional
  concluído, conforme a política escolhida pela empresa (NR-7, item 7.5.8, I).
* **Demissional sem bloqueio** (NR-7, item 7.5.11): o encerramento do contrato
  não trava. Um cron diário avalia os contratos encerrados: dispensa o exame
  quando o último exame clínico ocupacional tem menos de 135 dias (graus de
  risco 1 e 2 da NR-4) ou de 90 dias (graus 3 e 4, e também sem grau
  informado), e fora da dispensa abre uma atividade com prazo no término mais
  10 dias, encerrada quando o demissional é concluído.
* **Sigilo (LGPD art. 11)**: o grupo *Saúde Ocupacional* é distinto do RH, e a
  observação clínica só é visível a ele. O ASO em si não guarda diagnóstico.
