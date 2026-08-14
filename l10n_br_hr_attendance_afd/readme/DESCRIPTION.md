Importação e geração do **AFD - Arquivo Fonte de Dados**.

Suporta os dois leiautes que convivem hoje no mercado:

- **Portaria MTP 671/2021, Anexo V** (registros 1 a 7, 9 e bloco de
  assinatura), com validação de **CRC-16/KERMIT** e o campo hash SHA-256 do
  registro tipo 7 (REP-P);
- **Portaria 1.510/2009, Anexo I**, ainda gerado pelos REP-C certificados antes
  de 10/02/2022 (art. 96 da 671) - que é a base instalada da maioria dos
  clientes. Como esse leiaute grava hora local sem fuso, o fuso do
  estabelecimento é um parâmetro da importação.

O que a importação garante:

- **análise antes da gravação**: CRC, tamanho de registro, formato de data,
  continuidade de NSR e contagens do trailer são conferidos e apresentados
  antes de qualquer dado entrar na base;
- **idempotência**: reimportar o mesmo arquivo (ou o arquivo estendido da
  coleta seguinte) não duplica marcação, porque o par REP + NSR é único;
- **nada é descartado em silêncio**: marcação cujo CPF/PIS não bate com
  nenhum funcionário vira pendência, com ação para reconciliar depois que o
  documento for cadastrado;
- **lacuna de NSR vira alerta**: faixa ausente é indício de marcação suprimida
  e fica registrada no lote de importação.

A geração de AFD serve tanto para reexportar o que foi importado quanto para o
REP-P, e nomeia o arquivo conforme o item 10 do Anexo V.
