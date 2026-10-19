# Plano de execução do PRD de SST

Estado da implementação de `docs/PRD-sst-esocial.md`. Branch `16.0-hr-sst`, empilhada
sobre `16.0-esocial-ciclo-minimo` (PR #435), porque a Fase 0 do PRD (RS-01 e RS-02) já
está resolvida lá.

## Base herdada do PR #435 (Fase 0, não refazer)

- **RS-01** (RF-14): `base_intermediario._extract_id_evento` extrai o `Id` do XML e
  `action_gerar_evento` grava em `id_evento`. Ciclo transmissão -> recibo fecha.
- **RS-02**: `l10n_br.esocial.s1005` com CNAE preponderante, RAT, FAP, RAT ajustado,
  `buscar_vigente()` e `get_parametros_encargos()` (contrato consumido pelo GILRAT).

## Correções ao diagnóstico do PRD (verificado contra os bindings XSD da esociallib)

O PRD marcou como `[verificar]` a numeração das tabelas e o domínio do `tpExameOcup`.
Verificação feita contra `esociallib==0.1.3`, cujos bindings são gerados dos XSDs
oficiais do leiaute S-1.3, e contra os CSVs oficiais que a lib empacota:

| Item do PRD (§1.1, §3)                                  | Veredito                                                                                                             | Fonte                                                                                              |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| "Agentes nocivos é a Tabela 24 oficial"                 | **Errado.** É a Tabela 22 mesmo; o repo já está certo. A Tabela 24 é compatibilidade FPAS x classificação tributária | `tabela_22_agentes_nocivos_aposent_especial.csv` contém o código `09.01.001` citado no próprio PRD |
| "Financiamento da aposentadoria especial é a Tabela 02" | **Correto**                                                                                                          | `tabela_02_financiamento_aposent_especial.csv`                                                     |
| "CID não é tabela numerada do eSocial"                  | **Correto** (vem da CID-10)                                                                                          | ausência na lista de tabelas oficiais                                                              |
| "Demissional é código 9, não 8"                         | **Correto**: o CSV do repo estava errado                                                                             | enum `ExMedOcupTpExameOcup`                                                                        |
| "tipo_aso_3 deveria falar em risco ocupacional"         | **Correto**: o rótulo oficial é "mudança de função ou de mudança de risco ocupacional"                               | enum `ExMedOcupTpExameOcup`                                                                        |

Domínios extraídos dos bindings e usados nas Selections (nunca inventados) e reunidos em
`l10n_br_hr_sst/models/sst_dominios.py`: `AgNocTpAval`, `AgNocUnMed` (30 unidades),
`EpcEpiUtilizEpc`, `EpcEpiUtilizEpi`, `InfoAmbLocalAmb`, `RespRegIdeOc`, `AsoResAso`,
`ExameIndResult`, `ExameOrdExame`, `CatTpAcid`, `CatTpCat`, `CatIniciatCat`,
`EmitenteIdeOc`, `LocalAcidenteTpLocal`, `ParteAtingidaLateralidade`.

Builders disponíveis na esociallib 0.1.3: S-2210, S-2220, S-2221 e S-2240 existem;
**S-2245 não existe**, por isso o RS-22 ficou fora desta entrega.

## Módulos entregues

| Módulo                               | Requisitos           | Estado |
| ------------------------------------ | -------------------- | ------ |
| `l10n_br_hr_sst`                     | RS-03, RS-04         | pronto |
| `l10n_br_hr_sst_epi`                 | RS-05 a RS-08        | pronto |
| `l10n_br_hr_sst_aso`                 | RS-09 a RS-11, RS-20 | pronto |
| `l10n_br_hr_sst_cat`                 | RS-12, RS-13         | pronto |
| `l10n_br_esocial_sst`                | RS-14 a RS-17, RS-37 | pronto |
| `l10n_br_hr_payroll_sst`             | RS-18, RS-19         | pronto |
| `l10n_br_esocial` (dados + migração) | RS-30                | pronto |

## Decisões de arquitetura tomadas na implementação

1. **`l10n_br_hr_sst` depende de `l10n_br_esocial`**, e não apenas de `l10n_br_hr`. As
   tabelas de domínio que o modelo de risco referencia (agentes nocivos, aposentadoria
   especial, CID, parte do corpo, procedimentos diagnósticos) vivem no
   `l10n_br_esocial`. Extraí-las para um módulo menor mexeria num módulo em PR aberto
   sem ganho real: quem faz SST no Brasil transmite eSocial.
2. **A ficha de EPI não virou modelo próprio.** O PRD previa `l10n_br.sst.ficha.epi` com
   linhas, mas a pilha da OCA já modela a entrega (`hr.personal.equipment`) por
   trabalhador. A ficha virou **relatório PDF** sobre `hr.employee`, e a assinatura e o
   motivo de devolução ficaram na entrega, que é onde a NR-6 os exige. Um modelo
   paralelo duplicaria o histórico.
3. **O grupo `epiCompl` do S-2240 mora no Certificado de Aprovação.** As declarações
   (uso ininterrupto, periodicidade de troca, higienização) descrevem o equipamento, não
   o ambiente: o mesmo protetor auricular tem a mesma exigência em qualquer setor.
4. **"Apto com restrição" não existe no leiaute.** O campo `resAso` do S-2220 só admite
   apto ou inapto, então a restrição virou booleano com descrição, à parte do resultado
   que vai no evento.
5. **Insalubridade e periculosidade continuam editáveis** (compute com
   `readonly=False`): convenção coletiva e decisão judicial podem obrigar a pagar o que
   o laudo não aponta. O que o módulo garante é que a divergência apareça, com campo de
   justificativa. Contrato sem ambiente preserva o que já era pago.
6. **Afastamento do acidente usa o motivo 01 da Tabela 18** ("acidente/doença do
   trabalho") nas três espécies, inclusive doença ocupacional. O código 03 é
   "acidente/doença NÃO relacionada ao trabalho" e destruiria o nexo.

## Fora do escopo desta entrega

- RS-21 a RS-29 e RS-31 a RS-36 (P1 e P2 do PRD).
- RS-22 (S-2245): a esociallib não tem builder para o evento.
- Transmissão real ao ambiente do eSocial: os eventos são gerados e validados, mas o
  envio usa a infraestrutura de lote já existente no `l10n_br_esocial`.
