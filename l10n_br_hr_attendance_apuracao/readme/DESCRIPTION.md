Motor de apuração de jornada: transforma marcações em jornada apurada,
aplicando as regras materiais da CLT.

O que o motor faz por dia, para cada funcionário:

- **pareia** as marcações e acusa número ímpar de registros em vez de fabricar
  a marcação que falta (art. 74 da Portaria 671/2021);
- aplica a **tolerância** do art. 58, § 1º com a regra da Súmula 366 do TST:
  passou de 10 minutos no dia, computa-se o tempo integral, não o excedente;
- confere o **intervalo intrajornada** (art. 71), com mínimo parametrizável
  para acomodar norma coletiva até o piso de 30 minutos (art. 611-A, III), e
  calcula o **período suprimido** indenizável pelo § 4º;
- separa o **adicional noturno** (22h às 5h) e converte pela **hora reduzida**
  de 52min30s (art. 73, § 1º);
- classifica o excedente em **faixas de hora extra** (50% em dia útil, 100% em
  domingo e feriado);
- registra **faltas**, distinguindo a injustificada, e as **ocorrências**
  tipificadas nos quatro códigos do registro 07 do AEJ;
- verifica a **interjornada** de 11 horas (art. 66).

O fechamento da competência trava o recálculo, e o sistema recusa fechar
período com marcação sem par, marcação pendente de conciliação ou lacuna de
NSR conhecida: número que vai para o holerite e para o AEJ não pode carregar
problema conhecido em silêncio.

As regras de cálculo vivem em `models/regras_jornada.py`, em funções puras,
testáveis contra o texto legal sem banco de dados.
