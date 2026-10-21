Base da gestão de Saúde e Segurança do Trabalho (SST) brasileira.

Este módulo mantém o inventário de riscos ocupacionais que sustenta, com origem
documental, tudo o que vem depois: a entrega de EPI (NR-6), o controle de exames
ocupacionais (NR-7), o evento S-2240 do eSocial, o adicional de insalubridade ou
periculosidade na folha e o adicional de GILRAT da aposentadoria especial.

Modelos principais:

* **Ambiente de trabalho** (``l10n_br.sst.ambiente``) - corresponde ao grupo
  ``infoAmb`` do S-2240: setor, local e inscrição do estabelecimento.
* **Fator de risco** (``l10n_br.sst.risco``) - grupo ``agNoc``: agente nocivo da
  Tabela 24, avaliação quantitativa ou qualitativa, proteção coletiva e
  individual, enquadramento em aposentadoria especial e consequência trabalhista
  (insalubridade e periculosidade).
* **Laudo** (``l10n_br.sst.laudo``) - PGR, LTCAT, PCMSO ou AET, com vigência,
  responsável técnico e substituição do laudo anterior.
* **Responsável técnico** (``l10n_br.sst.responsavel``) - grupo ``respReg``,
  obrigatório no S-2240.

O contrato passa a apontar para o ambiente de trabalho, e daí se derivam os
riscos aplicáveis ao trabalhador, filtrados por função e por vigência.

A empresa guarda o **grau de risco da organização** (1 a 4, Quadro I da NR-4),
usado pela NR-7, entre outros pontos, no prazo de dispensa do exame demissional.

Insalubridade e periculosidade no mesmo fator de risco geram **aviso**, e não
bloqueio: o laudo descreve o ambiente e pode apontar os dois (radiação
ionizante está no Anexo 5 da NR-15 e na NR-16). O que não se acumula é o
pagamento (CLT, art. 193, par. 2, e TST IRR Tema 17), resolvido no contrato.
