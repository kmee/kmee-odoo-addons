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
  calculado** (primeiro dia útil seguinte, pulando fim de semana e os feriados
  da Tabela 84; imediato no óbito), alerta em cron e registro no chatter quando
  a comunicação sai fora do prazo.
* **Afastamento vinculado** (S-2230) com o motivo 01 da Tabela 18,
  acidente ou doença do trabalho, que é o que preserva o nexo com o acidente.
