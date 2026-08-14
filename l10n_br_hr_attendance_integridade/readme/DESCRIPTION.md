Verificação de integridade do **PTRP**: prova de qual programa gerou os
arquivos entregues à fiscalização, e detecção do que sai da versão coberta
pelo Atestado Técnico (art. 89 da Portaria MTP 671/2021).

## O escopo atestado, e por que ele não é o repositório inteiro

O Atestado declara que um programa atende aos requisitos da Portaria. O que
implementa esses requisitos é um subconjunto do código: leiaute do AFD e do
AEJ, motor de apuração, imutabilidade da marcação e espelho de ponto. Esse
subconjunto está declarado em `models/ptrp_escopo.py`, arquivo a arquivo.

A consequência prática é a que interessa no dia a dia: corrigir um rótulo de
tela, uma tradução, um teste ou o README **não altera o resumo digital** e
não obriga a revisar documento nenhum. Só mudança no escopo atestado dispara
a revisão, o que torna o versionamento uma decisão informada em vez de um
sobressalto a cada release.

## Duas camadas, porque uma sozinha engana

1. **Fonte**: resumo SHA-256 do escopo, calculado sobre um manifesto ordenado
   de `caminho:resumo`, com quebra de linha normalizada. O texto canônico é
   simples o bastante para ser reproduzido em qualquer linguagem - requisito
   de quem precisa conferir sem confiar na nossa implementação.

2. **Execução**: no Odoo dá para mudar o resultado de uma apuração **sem
   tocar em uma linha deste código** - basta um módulo que herde os modelos,
   uma ação de servidor em Python ou uma automação. Conferir só os arquivos
   daria uma resposta tranquilizadora e errada, então o módulo também lista
   quem estende os modelos do PTRP e que código está guardado no banco sobre
   eles.

## Onde a prova fica

Ao gerar o AEJ, a competência guarda o resumo, a situação da conferência e o
diagnóstico. Meses depois, quem responde "qual programa gerou este arquivo" é
o resumo gravado junto dele, não a versão instalada no dia da fiscalização.

## Configuração

- `l10n_br_hr_attendance_aej.ptrp_resumo_homologado`: resumo publicado pelo
  desenvolvedor que assina o Atestado;
- `l10n_br_hr_attendance_aej.ptrp_versao_atestada`: a versão a que o Atestado
  se refere.

Sem o resumo homologado configurado, o módulo continua calculando e gravando
o resumo, apenas sem poder afirmar se ele confere.
