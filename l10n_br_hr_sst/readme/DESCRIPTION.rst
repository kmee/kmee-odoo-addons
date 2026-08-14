Base da gestão de Saúde e Segurança do Trabalho (SST) brasileira.

Este módulo mantém o inventário de riscos ocupacionais que sustenta, com origem
documental, tudo o que vem depois: a entrega de EPI (NR-6), o controle de exames
ocupacionais (NR-7), o evento S-2240 do eSocial, o adicional de insalubridade ou
periculosidade na folha e o adicional de GILRAT da aposentadoria especial.

Modelos principais:

* **Ambiente de trabalho** (``l10n_br.sst.ambiente``) — corresponde ao grupo
  ``infoAmb`` do S-2240: setor, local e inscrição do estabelecimento.
* **Fator de risco** (``l10n_br.sst.risco``) — grupo ``agNoc``: agente nocivo da
  Tabela 22, avaliação quantitativa ou qualitativa, proteção coletiva e
  individual, enquadramento em aposentadoria especial e consequência trabalhista
  (insalubridade e periculosidade).
* **Laudo** (``l10n_br.sst.laudo``) — PGR, LTCAT, PCMSO ou AET, com vigência,
  responsável técnico e substituição do laudo anterior.
* **Responsável técnico** (``l10n_br.sst.responsavel``) — grupo ``respReg``,
  obrigatório no S-2240.

O contrato passa a apontar para o ambiente de trabalho, e daí se derivam os
riscos aplicáveis ao trabalhador, filtrados por função e por vigência.
