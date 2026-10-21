Registro de acidente de trabalho e emissão da CAT.

Desde 2023 o CATWeb foi descontinuado e a Comunicação de Acidente de Trabalho é
o próprio evento S-2210 do eSocial. Sem este registro, a empresa não tem como
cumprir o art. 22 da Lei 8.213/91, que manda comunicar o acidente até o primeiro
dia útil seguinte e, em caso de óbito, de imediato.

O módulo entrega:

* **Acidente de trabalho** típico, de trajeto ou doença ocupacional, com parte do
  corpo atingida (Tabela 13), agente causador (Tabela 14), situação geradora
  (Tabela 15), natureza da lesão (Tabela 17), CID, local do acidente e atestado
  médico com o emitente e seu órgão de classe.
* **CAT** inicial, de reabertura e de comunicação de óbito, com o **prazo legal
  calculado**, alerta em cron e registro no chatter quando a comunicação sai
  fora do prazo:

  * primeiro dia útil seguinte ao acidente; dia útil exclui sábado, domingo e
    feriado **nacional** (Lei 662/1949, Lei 6.802/1980 e Lei 14.759/2023).
    Carnaval, Sexta-feira da Paixão e Corpus Christi não são feriados
    nacionais; feriados estaduais e municipais contam quando configurados como
    folga geral no calendário de trabalho da empresa;
  * óbito: comunicação imediata, contada da data do óbito. Morte depois do dia
    útil seguinte não antecipa o prazo da CAT inicial;
  * doença ocupacional: o dia do acidente é o primeiro entre o início da
    incapacidade, a segregação compulsória e o diagnóstico (Lei 8.213/91,
    art. 23), calculado a partir dessas datas;
  * reabertura: sem prazo próprio.
* **Horas trabalhadas antes do acidente** no formato do S-1.3 (``TS_hora_99``,
  de 0000 a 9959), recusadas na doença ocupacional, como manda o leiaute.
* **Afastamento vinculado** (S-2230) com o motivo 01 da Tabela 18,
  acidente ou doença do trabalho, que é o que preserva o nexo com o acidente.
