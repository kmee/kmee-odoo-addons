# PRD — Saúde e Segurança do Trabalho (SST) para Odoo: EPI, ASO/PCMSO, CAT e eSocial

**Status:** rascunho para revisão · **Data:** 2026-08-12 · **Repositório-alvo:**
[kmee/kmee-odoo-addons](https://github.com/kmee/kmee-odoo-addons) (branch `16.0`) ·
**Escopo:** gestão de riscos ocupacionais, EPI, exames ocupacionais (ASO/PCMSO),
acidentes de trabalho (CAT) e os eventos SST do eSocial, integrados à folha de
pagamento.

> Terceiro documento da série. Complementa
> [`PRD-folha-pagamento-evolucao.md`](https://github.com/kmee/kmee-odoo-addons/blob/16.0/docs/PRD-folha-pagamento-evolucao.md)
> (motor de cálculo) e `PRD-controle-ponto-brasileiro.md` (jornada). Códigos de
> requisito com prefixo `RS-` (Requisito SST), sem colisão com os `RF-` (folha) e `RP-`
> (ponto).
>
> Itens **[verificar]** dependem de conferência contra o leiaute oficial do eSocial
> S-1.3 (NT 06/2026) — ver §11.

---

## 1. Contexto e problema

### 1.1 A frente de SST está mais avançada do que parece — e mais incompleta

O `l10n_br_esocial` **já carrega todas as tabelas oficiais de SST**, com dados
populados:

| Tabela eSocial                                                | Modelo no repo                             | CSV |
| ------------------------------------------------------------- | ------------------------------------------ | --- |
| Tab 13 — Parte do corpo atingida                              | `l10n_br.esocial.parte.corpo`              | ✅  |
| Tab 14 — Agente causador de acidente                          | `l10n_br.esocial.agente.causador`          | ✅  |
| Tab 15 — Situação geradora do acidente                        | `l10n_br.esocial.situacao.geradora`        | ✅  |
| Tab 17 — Natureza da lesão                                    | `l10n_br.esocial.natureza.lesao`           | ✅  |
| Tab 22 — Agentes nocivos                                      | `l10n_br.esocial.agente.nocivo`            | ✅  |
| Tab 23 — Aposentadoria especial                               | `l10n_br.esocial.aposentadoria.especial`   | ✅  |
| Tab 27 — Procedimentos diagnósticos                           | `l10n_br.esocial.procedimento.diagnostico` | ✅  |
| Tab 29 — Treinamentos e capacitações                          | `l10n_br.esocial.treinamento`              | ✅  |
| Tab 60 — CID                                                  | `l10n_br.esocial.cid`                      | ✅  |
| Tipos de ASO / Tipos de CAT / Financiamento aposent. especial | CSVs próprios                              | ✅  |

> **Atenção à numeração:** os números de tabela acima são os das `_description` dos
> modelos do repo e **divergem da numeração oficial do eSocial** em pelo menos dois
> casos: agentes nocivos é a **Tabela 24** oficial ("Agentes Nocivos e Atividades —
> Aposentadoria Especial", referenciada pelo campo `codAgNoc` do S-2240) e o
> financiamento da aposentadoria especial é a **Tabela 02**. O CID tampouco é uma tabela
> numerada do eSocial (vem da CID-10/11). O conteúdo dos CSVs parece correto; a
> rotulagem precisa ser conferida e alinhada à oficial antes de gerar XML.
> **[verificar]**

**Mas nenhum evento de SST está implementado.** Os intermediários existentes em
`l10n_br_esocial/models/intermediarios/` são apenas: `s1000`, `s1010`, `s1020`, `s1200`,
`s2200`, `s2206`, `s2230`, `s2299`. Faltam **S-2210, S-2220, S-2240 e S-2245** — e
também o **S-1005**, que é pré-requisito dos três primeiros.

Ou seja: alguém já fez o trabalho chato de mapear e popular as tabelas de domínio, e ele
está parado sem uso. O custo de entrada da frente de SST é **menor do que aparenta**.

### 1.2 O que não existe de forma alguma

Nenhum modelo de negócio de SST: não há EPI, Certificado de Aprovação (CA), ficha de
entrega, exame ocupacional, ASO, PCMSO, PGR/GRO, inventário de riscos, LTCAT, acidente
de trabalho, CAT, treinamento de NR, CIPA ou SESMT. Zero ocorrências no repositório.

### 1.3 Insalubridade e periculosidade estão na folha, mas desconectadas do laudo

`l10n_br_hr_payroll` **calcula** os dois adicionais, mas a partir de **flags digitados à
mão no contrato**:

- `hr_contract.py:11-24` — `l10n_br_periculosidade` (Boolean), `l10n_br_insalubridade`
  (Boolean), `l10n_br_grau_insalubridade` (Selection mínimo/médio/máximo);
- `hr_salary_rule_data.xml:92-124` — periculosidade = 30% de `contract.wage` (correto,
  art. 193 §1º CLT / Súmula 191 TST); insalubridade = 10/20/40% do **salário mínimo**;
- `hr_contract.py:64-71` — constraint correta impedindo acúmulo (Súmula 364 TST).

Dois problemas:

1. **Sem origem documental.** O adicional é uma caixinha marcada por quem preenche o
   contrato, não a consequência de um laudo (PGR/LTCAT) e de uma avaliação de risco. Em
   fiscalização ou ação trabalhista, é o laudo que sustenta o pagamento — e é ele que
   também precisa sustentar o **S-2240**. Hoje as duas informações podem divergir sem
   que nada acuse.
2. **Base da insalubridade fixa em salário mínimo.** Defensável (Súmula Vinculante 4 do
   STF vedou a substituição por via judicial; a Súmula 228 do TST está suspensa), mas
   muitas convenções coletivas fixam o **piso da categoria** como base. Deveria ser
   parametrizável — provavelmente via `l10n_br_hr_syndicate`. **[verificar com o
   fiscal]**

### 1.4 O elo que o cliente está sentindo

O que motiva este PRD é uma cadeia de dependências que só fecha inteira:

```
PGR/LTCAT (laudo) → risco por ambiente/função
        ├──→ EPI entregue (NR-6, CA)   ──┐
        ├──→ ASO / PCMSO (NR-7)          ├──→ eSocial S-2240 ──→ PPP eletrônico (INSS)
        ├──→ adicional insalub./pericul. ┘                  └──→ adicional GILRAT 6/9/12%
        └──→ acidente → CAT (S-2210) ──→ FAP ──→ alíquota RAT ajustado ──→ folha
```

Sem os módulos de SST, **nada dessa cadeia existe no Odoo** — e a empresa de porte médio
para cima simplesmente não pode operar, porque os eventos SST são obrigatórios para
**todos** os grupos do eSocial, inclusive MEI/ME/EPP.

---

## 2. Marco legal e regulatório

### 2.1 Eventos SST do eSocial (leiaute S-1.3, NT 06/2026)

| Evento     | Nome                                                   | Prazo de envio                                                                                 | Conteúdo essencial                                                                                                                                                                                                                                                                                                                        |
| ---------- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **S-2210** | Comunicação de Acidente de Trabalho (CAT)              | Até o **1º dia útil seguinte** ao acidente; **imediato em caso de óbito**                      | Tipo (inicial/reabertura/óbito), data/hora, local, parte do corpo, agente causador, situação geradora, natureza da lesão, CID, atestado médico, houve afastamento                                                                                                                                                                         |
| **S-2220** | Monitoramento da Saúde do Trabalhador (ASO)            | Até o **dia 15 do mês seguinte** ao exame                                                      | Tipo de exame (admissional, periódico, retorno, mudança de risco, monitoração pontual, demissional), data, médico responsável (CRM/UF), resultado (apto/inapto), exames complementares (Tab 27), ordem (inicial/sequencial)                                                                                                               |
| **S-2240** | Condições Ambientais do Trabalho — Agentes Nocivos     | Até o **dia 15 do mês seguinte** ao início da exposição, alteração ou obrigatoriedade          | Ambiente de trabalho (`infoAmb`), setor, descrição da atividade, **fatores de risco** (`codAgNoc`, **Tabela 24 oficial**; ausência de risco = código 09.01.001), intensidade/técnica de medição, **EPC/EPI** (`utilizEPC`, `eficEpc`, `utilizEPI`, `eficEpi`, `docAval` = **nº do CA**, `dscEPI`), responsável pelos registros ambientais |
| **S-2221** | Exame Toxicológico do Motorista Profissional Empregado | Até o **dia 15 do mês seguinte** ao exame (pré-admissional: dia 15 do mês seguinte à admissão) | Obrigatório para motoristas profissionais **categorias C, D e E** (Lei 13.103/2015): data do exame, laboratório (CNPJ), médico responsável, código do exame                                                                                                                                                                               |
| **S-2245** | Treinamentos, Capacitações, Exercícios Simulados       | Até o **dia 15 do mês seguinte** à conclusão do treinamento **[verificar]**                    | Treinamento de NR realizado, carga horária, tipo (Tab 29), profissional responsável                                                                                                                                                                                                                                                       |
| **S-1005** | Tabela de Estabelecimentos e Obras                     | Antes dos eventos que o referenciam                                                            | CNAE preponderante, **alíquota RAT**, **FAP**, RAT ajustado, informações de aposentadoria especial e processos administrativos/judiciais                                                                                                                                                                                                  |

**Ponto de arquitetura:** o **EPI não é um módulo de almoxarifado que "também" fala com
o eSocial**. O grupo `epiEpc` é parte estrutural do S-2240 — o nº do CA vai no campo
`docAval`, e a eficácia declarada do EPI é o que sustenta (ou derruba) o enquadramento
em aposentadoria especial. Controle de EPI e eSocial são **o mesmo dado**.

### 2.2 Normas Regulamentadoras

| NR                | Objeto                                                                                                                                                                                                                                                                                       | Impacto no sistema                                                 |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| **NR-1**          | GRO — Gerenciamento de Riscos Ocupacionais; **PGR** (inventário de riscos + plano de ação), que substituiu o PPRA em 2022                                                                                                                                                                    | Modelo de risco por ambiente/função é a fonte do S-2240            |
| **NR-4**          | SESMT — dimensionamento por grau de risco e nº de empregados                                                                                                                                                                                                                                 | Cadastro e dimensionamento (P2)                                    |
| **NR-5**          | CIPA — agora "Comissão Interna de Prevenção de Acidentes **e de Assédio**" (Lei 14.457/2022)                                                                                                                                                                                                 | Mandato, eleição, atas (P2)                                        |
| **NR-6**          | **EPI** — obrigação de fornecer gratuitamente, exigir uso, treinar, higienizar, substituir e **registrar a entrega**. Só pode ser comercializado/usado EPI com **CA** válido. A **Portaria SIT 107/2009** autorizou registro em livro, ficha **ou sistema eletrônico, inclusive biométrico** | Ficha de EPI digital com assinatura eletrônica é legalmente aceita |
| **NR-7**          | **PCMSO** — programa coordenado por médico do trabalho; **ASO** obrigatório nos tipos admissional, periódico, retorno ao trabalho, **mudança de riscos ocupacionais** (nomenclatura atualizada pela NR-7/2020) e demissional; **relatório analítico anual**                                  | Agendamento, controle de vencimento e bloqueios                    |
| **NR-9**          | Avaliação e controle da exposição a agentes físicos, químicos e biológicos                                                                                                                                                                                                                   | Intensidade/concentração e técnica de medição do S-2240            |
| **NR-15 / NR-16** | Insalubridade (10/20/40%) e periculosidade (30%)                                                                                                                                                                                                                                             | Já implementadas na folha, sem origem no laudo (§1.3)              |

### 2.3 PPP eletrônico e aposentadoria especial

- Desde **01/01/2023** o **PPP é exclusivamente eletrônico** (Portaria MTP nº 334/2022)
  e é **gerado pelo INSS a partir do S-2240** — a empresa não emite mais o papel.
- As informações do S-2240 vêm do **LTCAT** e devem ser atualizadas sempre que houver
  mudança nos riscos (não há obrigação de atualização anual).
- Exposição a agente nocivo enseja **alíquota adicional de GILRAT** para financiar a
  aposentadoria especial: **12% (15 anos), 9% (20 anos) ou 6% (25 anos)** — a tabela já
  está no repo (`l10n_br.esocial.financiamento.aposent.csv`), mas **não há nenhuma
  rubrica patronal** que a aplique (é o mesmo buraco do **RF-31** do PRD de folha).
- **Consequência de errar:** S-2240 mal informado gera PPP errado, aposentadoria
  especial negada ao trabalhador e ação regressiva/reclamatória contra a empresa. É um
  dos poucos eventos do eSocial cujo erro atinge diretamente o **direito previdenciário
  do empregado**, não só o caixa da empresa.

### 2.4 CAT e FAP — o impacto financeiro

- **Lei 8.213/91, art. 22**: a CAT deve ser comunicada até o **1º dia útil** seguinte ao
  acidente e **de imediato** em caso de óbito, sob pena de multa. Abrange acidente
  típico, **de trajeto** e **doença ocupacional**.
- Desde 2023 o **S-2210 é o próprio registro da CAT** — o antigo CATWeb foi
  descontinuado e a comunicação passou a ser feita exclusivamente pelo eSocial. Ou seja:
  sem o RS-14, a empresa **não tem como** cumprir o art. 22 da Lei 8.213/91.
- A acidentalidade da empresa alimenta o **FAP** (0,5 a 2,0), que multiplica a alíquota
  **RAT** (1/2/3%). Um FAP alto pode **dobrar** a contribuição patronal de RAT; um FAP
  bom **reduz pela metade**.
- Portanto SST não é só compliance: é uma alavanca direta sobre a folha patronal — o que
  liga esta frente ao **RF-31** (encargos patronais) do PRD de folha, hoje inexistente.

### 2.5 LGPD — dado pessoal sensível

Dados de saúde são **dados pessoais sensíveis** (Lei 13.709/2018, art. 11). Implicações
concretas de projeto:

- o **ASO não contém diagnóstico** — apenas apto/inapto e os riscos avaliados; o
  diagnóstico é sigilo médico e fica no prontuário, fora do alcance do RH;
- o prontuário ocupacional (NR-7) deve ficar sob guarda do **médico coordenador**, com
  acesso segregado do RH — no Odoo, isso exige grupos e regras de registro próprios, não
  apenas "grupo RH";
- retenção mínima de **20 anos** para prontuário ocupacional (NR-7) — muito além dos 5
  anos trabalhistas.

---

## 3. Diagnóstico: o que existe × o que falta

| Área                                                 | Situação hoje                                                                         | Ação                                                      |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Tabelas de domínio SST do eSocial                    | ✅ Completas e populadas                                                              | Reusar                                                    |
| Eventos S-2210 / S-2220 / S-2240 / S-2245            | ❌ Inexistentes                                                                       | Construir                                                 |
| Evento S-1005 (RAT/FAP/estabelecimento)              | ❌ Inexistente (já era pendência RF-25)                                               | Construir — pré-requisito                                 |
| Infra de transmissão eSocial (lote, retorno, recibo) | ⚠️ Existe, mas com o bug **RF-14** (`id_evento` nunca atribuído → retorno nunca casa) | **Corrigir antes**, senão nenhum evento SST fecha o ciclo |
| Gestão de EPI / CA / ficha                           | ❌ Inexistente                                                                        | Construir                                                 |
| ASO / PCMSO / exames                                 | ❌ Inexistente (só a tabela de tipos de ASO)                                          | Construir                                                 |
| PGR / GRO / inventário de riscos / LTCAT             | ❌ Inexistente                                                                        | Construir                                                 |
| CAT / acidentes                                      | ❌ Inexistente (tabelas prontas)                                                      | Construir                                                 |
| Treinamentos de NR                                   | ❌ Inexistente (tabela pronta)                                                        | Construir                                                 |
| Insalubridade / periculosidade na folha              | ⚠️ Calculadas, mas por flag manual sem laudo                                          | Ligar ao laudo                                            |
| Adicional GILRAT (aposentadoria especial)            | ❌ Inexistente (tabela pronta)                                                        | Construir (junto com RF-31)                               |
| Afastamento S-2230                                   | ✅ Implementado                                                                       | Ligar ao acidente/CAT                                     |
| CIPA / SESMT                                         | ❌ Inexistente                                                                        | P2                                                        |

**Achados incidentais nos dados existentes** (conferir contra o leiaute oficial antes de
gerar qualquer XML — todos **[verificar]**):

1. `l10n_br.esocial.tipo.aso.csv` traz `tipo_aso_3 = "De mudança de função"`; a NR-7
   (2020) e o leiaute atual usam **"mudança de riscos ocupacionais"**.
2. O mesmo CSV usa **código 8 para o demissional**; no campo `tpExameOcup` do S-2220 o
   demissional é, salvo engano, o código **9** (a série oficial é 0, 1, 2, 3, 4, 9). Se
   confirmado, é erro de dado que produziria XML rejeitado.
3. A numeração de tabelas nas `_description` dos modelos diverge da oficial (ver nota em
   §1.1): agentes nocivos = Tabela 24, financiamento = Tabela 02, "Tab 60 — CID" não é
   tabela do eSocial.

**Reuso de OCA:** ver §4.0 — há bem mais pronto na OCA do que a primeira leitura
sugeria, em especial a pilha `hr_personal_equipment_request` → `hr_employee_ppe` (OCA/hr
16.0), que já resolve o esqueleto de EPI. Nada disso tem aderência brasileira (não
modelam CA com validade, PGR, nem os campos do eSocial), mas servem de **base**, não só
de referência.

---

## 4. Arquitetura de módulos proposta

```
hr, l10n_br_hr
 └── l10n_br_hr_sst .................... base: riscos, ambientes, PGR/GRO, laudos (LTCAT/PGR)
      ├── l10n_br_hr_sst_epi .......... EPI, CA, ficha de entrega, estoque (depende de stock)
      ├── l10n_br_hr_sst_aso .......... PCMSO, exames, ASO, agendamento e bloqueios
      ├── l10n_br_hr_sst_cat .......... acidentes, CAT, investigação, ligação com S-2230
      ├── l10n_br_hr_sst_treinamento .. treinamentos de NR e reciclagens
      ├── l10n_br_esocial_sst ......... S-1005, S-2210, S-2220, S-2240, S-2245
      ├── l10n_br_hr_payroll_sst ...... insalub./pericul. a partir do laudo + adicional GILRAT
      └── l10n_br_hr_sst_cipa_sesmt ... CIPA (Lei 14.457/2022) e SESMT (NR-4)     [P2]
```

### 4.0 Reuso de módulos OCA (verificado na 16.0)

A regra adotada: **estender o que a OCA já mantém, criar só o que é especificamente
brasileiro.** Isso reduz superfície de código próprio e reaproveita testes e manutenção
da comunidade.

| Módulo OCA (16.0)                                                         | Repo                  | O que resolve                                                                                                                                                                                                                                         | O que ainda falta (nosso escopo)                                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`hr_personal_equipment_request`**                                       | OCA/hr                | Modelo `hr.personal.equipment` (alocação por empregado, produto, quantidade, UoM, `start_date`/`expiry_date`, máquina de estados requisitado→aceito→válido→expirado), `mail.thread` e requisição de equipamento                                       | —                                                                                                                                                                                                                                                                  |
| **`hr_employee_ppe`**                                                     | OCA/hr                | Marca produto como EPI (`is_ppe`), validade e duração (`expirable_ppe`, `ppe_duration`, `ppe_interval_type`), campo `certification` (nº de certificação), `issued_by`, **cron diário que expira alocações vencidas** e **relatório de recibo de EPI** | CA como **entidade própria** (validade do CA é do fabricante, não da entrega), vínculo ao risco neutralizado, assinatura eletrônica do trabalhador, campos do S-2240 (`docAval`/`dscEPI`/`eficEpi`), bloqueio de entrega com CA vencido, motivo de troca/devolução |
| **`hr_personal_equipment_stock`**                                         | OCA/hr                | Integra requisição de EPI com estoque: gera `stock.move`, baixa ao entregar, trata _backorder_                                                                                                                                                        | —                                                                                                                                                                                                                                                                  |
| **`hr_personal_equipment_request_tier_validation`**                       | OCA/hr                | Aprovação em camadas da requisição de EPI                                                                                                                                                                                                             | —                                                                                                                                                                                                                                                                  |
| **`hr_employee_medical_examination`**                                     | OCA/hr                | Modelo `hr.employee.medical.examination` (data, resultado, estados, `mail.thread`), wizard de geração em massa e **`ir.rule` que já restringe o usuário comum aos próprios exames**                                                                   | Tipo de ASO (Tab), médico + CRM/UF, clínica, exames complementares (Tab 27), vencimento, ordem, PCMSO, e a segregação mais forte exigida pela LGPD art. 11                                                                                                         |
| **`mgmtsystem_hazard` / `_nonconformity` / `_action` / `_health_safety`** | OCA/management-system | Perigos, não conformidades, **plano de ação corretiva/preventiva** e auditorias                                                                                                                                                                       | Usar como motor do **plano de ação do PGR** (RS-21) e da **investigação de acidente** (§4.4), em vez de modelar do zero                                                                                                                                            |
| **`base_tier_validation`**                                                | OCA/server-ux         | Fluxo de aprovação genérico — já presente na _stack_ do repo (`sale_tier_validation_exceptions`)                                                                                                                                                      | Aplicar a CAT, alteração de laudo e requisição de EPI                                                                                                                                                                                                              |
| **`auditlog`**                                                            | OCA/server-tools      | Trilha de auditoria por modelo/campo                                                                                                                                                                                                                  | Cobre a exigência de rastreabilidade de alteração de risco (R5) e o _log_ de acesso a dados de saúde (RS-20)                                                                                                                                                       |
| **`queue_job`**                                                           | OCA/queue             | Jobs assíncronos com canais                                                                                                                                                                                                                           | Geração em massa de S-2240 e reprocessamento (R2)                                                                                                                                                                                                                  |
| **`report_qweb_signer`**                                                  | OCA/reporting-engine  | **Assina PDF com certificado PKCS#12**                                                                                                                                                                                                                | Ficha de EPI e ASO assinados, sem escrever camada de assinatura                                                                                                                                                                                                    |
| **`l10n_br_fiscal_certificate`**                                          | OCA/l10n-brazil       | Gestão de **certificado A1** (armazenamento, validade, alertas)                                                                                                                                                                                       | Reusar em vez de criar cadastro de certificado próprio                                                                                                                                                                                                             |
| **`privacy` / `privacy_consent`**                                         | OCA/data-protection   | Base de conformidade LGPD/GDPR e consentimento                                                                                                                                                                                                        | Apoio ao RS-20 e à política de retenção                                                                                                                                                                                                                            |
| **`report_py3o` / `report_xlsx`**                                         | OCA/reporting-engine  | Relatórios ODT/DOCX e XLSX — `report_py3o` **já é usado no repo**                                                                                                                                                                                     | Ficha de EPI, ASO, relatório analítico do PCMSO                                                                                                                                                                                                                    |

**Efeito no escopo:** os requisitos de EPI (RS-05 a RS-08) e de exames (RS-09 a RS-11)
deixam de ser "construir do zero" e passam a ser "estender e brasileirizar" — o que
retira, por estimativa grosseira, boa parte do esforço das Fases 2 e 3.

### 4.1 `l10n_br_hr_sst` (base)

O modelo de risco, que é a fonte de tudo:

- `l10n_br.sst.ambiente` — ambiente de trabalho (`infoAmb` do S-2240): descrição,
  estabelecimento (CNPJ), tipo de inscrição, setor;
- `l10n_br.sst.risco` — fator de risco por ambiente **e/ou** função: agente nocivo (Tab
  22), intensidade/concentração, técnica de medição, limite de tolerância,
  **enquadramento em aposentadoria especial** (Tab 23);
- `l10n_br.sst.laudo` — PGR, LTCAT, PCMSO, AET: tipo, vigência, responsável técnico
  (nome, NIT, registro no conselho), anexo do documento;
- `l10n_br.sst.responsavel` — responsável pelos registros ambientais (campo obrigatório
  do S-2240);
- vínculo `hr.job` / `hr.contract` → riscos aplicáveis, que é o que permite derivar tudo
  o mais automaticamente.

### 4.2 `l10n_br_hr_sst_epi` — extensão de `hr_employee_ppe`

**Depende de `hr_employee_ppe`, `hr_personal_equipment_stock` e
`hr_personal_equipment_request_tier_validation`.** A alocação, o estoque, a expiração
por cron, a aprovação e o recibo já vêm prontos. O que este módulo acrescenta é o que a
legislação brasileira exige e a OCA não modela:

- `l10n_br.sst.ca` — Certificado de Aprovação como **entidade própria**: número,
  validade, fabricante, tipo de EPI, risco que neutraliza. O campo `certification`
  (Char) do `hr_employee_ppe` vira um M2O para este modelo — o CA tem validade própria,
  do fabricante, independente da data de entrega, e **um CA vencido invalida todas as
  entregas que dependem dele**;
- vínculo EPI ↔ **risco neutralizado** (`l10n_br.sst.risco`), que é o que alimenta o
  `epiEpc` do S-2240;
- **assinatura eletrônica do trabalhador** na ficha (portal ou biometria — autorizada
  pela Portaria SIT 107/2009), assinando o PDF via `report_qweb_signer`;
- **bloqueio** de entrega com CA vencido (a OCA expira a _alocação_, não valida o _CA_);
- motivo de troca/devolução, exigido pela NR-6;
- ficha de EPI em PDF com histórico completo, estendendo o relatório de recibo
  existente.

### 4.3 `l10n_br_hr_sst_aso` — extensão de `hr_employee_medical_examination`

**Depende de `hr_employee_medical_examination`**, que já entrega o modelo de exame com
estados, `mail.thread`, wizard de geração em massa e — relevante para a LGPD — uma
`ir.rule` restringindo o usuário comum aos próprios exames. O módulo OCA é raso (só
`date`, `result` passed/failed, `note`), então o acréscimo é substancial:

- `l10n_br.sst.pcmso` — programa por estabelecimento, médico coordenador, vigência,
  **relatório analítico anual** (NR-7);
- extensão do exame com os campos do **S-2220**: tipo de ASO (tabela já no repo), médico
  examinador (nome, CRM, UF), clínica, resultado no padrão brasileiro (apto / inapto /
  apto com restrição), exames complementares (Tab 27), próximo vencimento, ordem;
- **agendamento automático**: admissional na contratação, periódico conforme PCMSO (com
  periodicidade por faixa etária e risco), retorno após afastamento > 30 dias,
  demissional na rescisão;
- **bloqueios**: alertar (ou impedir, conforme política) admissão sem ASO admissional,
  retorno de afastamento sem ASO de retorno e rescisão sem ASO demissional;
- painel de vencimentos.

### 4.4 `l10n_br_hr_sst_cat`

- `l10n_br.sst.acidente` — data/hora, local, tipo (típico/trajeto/doença ocupacional),
  parte do corpo (Tab 13), agente causador (Tab 14), situação geradora (Tab 15),
  natureza da lesão (Tab 17), CID (Tab 60), houve afastamento, houve óbito, houve
  registro policial, testemunhas;
- **CAT** (inicial / reabertura / comunicação de óbito) com alerta de prazo do **1º dia
  útil** e tratamento imediato para óbito;
- integração com o **S-2230** (afastamento) já existente: acidente com afastamento gera
  o afastamento vinculado, com o motivo correto;
- investigação de acidente e plano de ação — reusando `mgmtsystem_nonconformity` e
  `mgmtsystem_action` (OCA/management-system) em vez de modelar plano de ação próprio;
- indicadores de acidentalidade (taxa de frequência e gravidade) — insumo do FAP.

### 4.5 `l10n_br_esocial_sst`

Intermediários seguindo o padrão de `base_intermediario.py`: `s1005_estabelecimento`,
`s2210_cat`, `s2220_monitoramento_saude`, `s2240_condicoes_ambientais`,
`s2245_treinamentos` e — quando houver motorista profissional na base —
`s2221_exame_toxicologico`. **Depende da correção do RF-14** (matching de retorno por
`id_evento`), sem a qual nenhum evento fecha o ciclo transmissão → recibo.

Regras de negócio que valem código dedicado:

- **S-2240 é por trabalhador e tem histórico**: cada alteração de risco gera novo evento
  com nova data de início; não é um "cadastro" que se sobrescreve;
- geração de S-2240 **em massa** ao alterar o laudo de um ambiente (afeta N
  trabalhadores);
- validação cruzada: `utilizEPI = "sim"` exige `docAval` (nº do CA) **ou** `dscEPI`;
  risco 09.01.001 (ausência de risco) exige `utilizEPC`/`utilizEPI` = "não aplicável".

### 4.6 `l10n_br_hr_payroll_sst` (a ponte com a folha)

- `contract.l10n_br_insalubridade` / `l10n_br_periculosidade` /
  `l10n_br_grau_insalubridade` passam a ser **derivados do risco vigente** (`compute`
  com `readonly=False` e justificativa quando sobrescritos), com alerta quando o
  contrato divergir do laudo;
- base da insalubridade parametrizável (salário mínimo × piso da categoria via
  `l10n_br_hr_syndicate`) **[verificar com o fiscal]**;
- **rubrica patronal de adicional GILRAT** (6/9/12%) para quem tem exposição ensejadora
  de aposentadoria especial, alimentando o S-1200 — implementar junto com o **RF-31**;
- RAT ajustado (RAT × FAP) vindo do S-1005, por estabelecimento.

---

## 5. Requisitos priorizados

### P0 — o mínimo para a empresa operar legalmente

**Pré-requisitos (bloqueiam tudo)**

- **RS-01** — Corrigir o **RF-14** do PRD de folha (`id_evento` do eSocial nunca
  atribuído). Sem isso nenhum evento SST recebe recibo. _Caminho crítico._
- **RS-02** — Implementar o **S-1005** (estabelecimentos): CNAE preponderante, alíquota
  RAT, FAP, RAT ajustado. Pré-requisito dos eventos SST **e** dos encargos patronais
  (RF-31).

**Base de riscos**

- **RS-03** — Modelos `l10n_br.sst.ambiente`, `l10n_br.sst.risco` e `l10n_br.sst.laudo`,
  com vínculo a função/contrato e enquadramento em aposentadoria especial.
- **RS-04** — Responsável pelos registros ambientais (campo obrigatório do S-2240).

**EPI (NR-6)** — sobre a pilha `hr_personal_equipment_request` → `hr_employee_ppe`

- **RS-05** — Cadastro de **CA** como entidade própria, com validade e alerta de
  vencimento; `certification` do `hr_employee_ppe` passa a apontar para ele.
- **RS-06** — Vínculo EPI ↔ risco neutralizado (insumo do `epiEpc` do S-2240). _Estoque
  e ciclo de vida já vêm de `hr_personal_equipment_stock` e do cron de expiração._
- **RS-07** — **Assinatura eletrônica do trabalhador** na ficha de EPI (via
  `report_qweb_signer`), com motivo de troca/devolução.
- **RS-08** — Bloqueio de entrega com CA vencido; ficha em PDF para fiscalização
  (estendendo o relatório de recibo da OCA).

**Exames (NR-7)** — sobre `hr_employee_medical_examination`

- **RS-09** — Estender o exame da OCA com os campos do **S-2220** (tipo de ASO, médico +
  CRM/UF, clínica, resultado apto/inapto/apto-com-restrição, exames complementares,
  vencimento, ordem).
- **RS-10** — Agendamento automático dos ASOs (admissional, periódico, retorno,
  demissional) e painel de vencimentos.
- **RS-11** — Bloqueios/alertas de admissão, retorno e rescisão sem o ASO
  correspondente.

**Acidentes**

- **RS-12** — Registro de acidente e emissão de **CAT** (inicial/reabertura/óbito) com
  alerta do prazo do 1º dia útil.
- **RS-13** — Vínculo acidente → afastamento (**S-2230** existente) com o motivo
  correto.

**Eventos eSocial**

- **RS-14** — **S-2210** (CAT).
- **RS-15** — **S-2220** (monitoramento da saúde / ASO).
- **RS-16** — **S-2240** (condições ambientais), incluindo o grupo `epiEpc` alimentado
  pela ficha de EPI e pelo CA, com geração em massa a partir da alteração de laudo.
- **RS-17** — Validações cruzadas do S-2240 (`docAval`/`dscEPI`, ausência de risco,
  `eficEpi`) **antes** do envio, para não descobrir erro no retorno.

**Folha**

- **RS-18** — Insalubridade/periculosidade derivadas do laudo, com alerta de divergência
  entre contrato e risco vigente.
- **RS-19** — Rubrica patronal de **adicional GILRAT** (6/9/12%) para exposição
  ensejadora de aposentadoria especial, refletida no S-1200.

**Sigilo**

- **RS-20** — Segregação de acesso a dados de saúde (LGPD art. 11): grupo de saúde
  ocupacional distinto do grupo RH; ASO sem diagnóstico; prontuário fora do alcance do
  RH. Partir da `ir.rule` que o `hr_employee_medical_examination` já traz e endurecê-la;
  `auditlog` (OCA/server-tools) para o registro de acesso.

### P1 — completude operacional

- **RS-21** — **PGR/GRO** (NR-1): inventário de riscos e plano de ação com responsáveis
  e prazos, reusando `mgmtsystem_hazard`/`_action`/`_nonconformity`.
- **RS-22** — **S-2245** (treinamentos de NR) com controle de reciclagem e alerta de
  vencimento.
- **RS-23** — Relatório analítico anual do **PCMSO** (NR-7).
- **RS-24** — Espelho do **PPP** (conferência interna do que foi enviado ao S-2240, já
  que o documento oficial passou a ser emitido pelo INSS).
- **RS-25** — Indicadores de acidentalidade (taxa de frequência e gravidade) e simulação
  de impacto no FAP/RAT.
- **RS-26** — Portal do empregado: assinar ficha de EPI, ver ASOs e treinamentos.
- **RS-27** — Requisição/reposição de EPI integrada a compras, com ponto de pedido.
- **RS-28** — Retenção de 20 anos do prontuário ocupacional (NR-7) e política de
  descarte.
- **RS-29** — Base da insalubridade parametrizável por convenção coletiva
  (`l10n_br_hr_syndicate`).
- **RS-30** — Correção dos dados de domínio existentes: descrição do tipo de ASO 3
  ("mudança de riscos ocupacionais"), **código do demissional (8 → 9)** e alinhamento da
  numeração das tabelas à oficial (ver achados em §3).
- **RS-37** — **S-2221** (exame toxicológico do motorista profissional, Lei
  13.103/2015): cadastro do exame (laboratório/CNPJ, médico, código) e evento com prazo
  do dia 15. Condicional: só entra no escopo de clientes com motoristas categorias C/D/E
  — mas o transporte é um dos setores que **mais usa** controle de ponto físico e SST,
  então a chance de aparecer cedo é alta.

### P2 — maturidade

- **RS-31** — **CIPA** (NR-5 + Lei 14.457/2022, incluindo a competência de prevenção do
  assédio): mandato, eleição, atas, plano de ação.
- **RS-32** — **SESMT** (NR-4): dimensionamento por grau de risco e nº de empregados.
- **RS-33** — Integração com clínicas/medicina do trabalho (importação de ASO por
  arquivo/API dos sistemas de SOC mais usados no mercado).
- **RS-34** — Ordens de serviço de segurança (NR-1) com ciência do trabalhador.
- **RS-35** — App/quiosque para entrega de EPI com leitura de código de barras.
- **RS-36** — Painel único de conformidade SST por estabelecimento (ASOs vencidos, CAs
  vencidos, EPIs pendentes, eventos rejeitados, CATs no prazo).

---

## 6. Modelo de dados (esboço)

| Modelo                        | Papel                    | Campos-chave                                                                                                                                                                              |
| ----------------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `l10n_br.sst.ambiente`        | Ambiente / `infoAmb`     | `nome`, `company_id`, `cnpj`, `tipo_inscricao`, `setor`, `descricao_atividade`                                                                                                            |
| `l10n_br.sst.risco`           | Fator de risco           | `ambiente_id`, `job_ids`, `agente_nocivo_id`, `intensidade`, `tecnica_medicao`, `limite_tolerancia`, `aposentadoria_especial_id`, `insalubridade_grau`, `periculosidade`                  |
| `l10n_br.sst.laudo`           | PGR/LTCAT/PCMSO/AET      | `tipo`, `date_from`, `date_to`, `responsavel_id`, `anexo`, `risco_ids`                                                                                                                    |
| `l10n_br.sst.ca`              | Certificado de Aprovação | `numero`, `validade`, `fabricante`, `tipo_epi`, `risco_neutralizado_ids`                                                                                                                  |
| `l10n_br.sst.ficha.epi`       | Ficha do trabalhador     | `employee_id`, `linha_ids`, `assinatura`, `data_assinatura`                                                                                                                               |
| `l10n_br.sst.ficha.epi.linha` | Movimento de EPI         | `product_id`, `ca_id`, `tipo` (entrega/devolução/troca), `date`, `quantidade`, `motivo`, `picking_id`                                                                                     |
| `l10n_br.sst.pcmso`           | Programa                 | `company_id`, `medico_coordenador_id`, `date_from`, `date_to`, `relatorio_anual`                                                                                                          |
| `l10n_br.sst.exame`           | Exame / ASO              | `employee_id`, `tipo_aso_id`, `date`, `medico_nome`, `crm`, `uf_crm`, `resultado`, `procedimento_ids`, `date_vencimento`, `ordem`                                                         |
| `l10n_br.sst.acidente`        | Acidente                 | `employee_id`, `datetime`, `local`, `tipo`, `parte_corpo_id`, `agente_causador_id`, `situacao_geradora_id`, `natureza_lesao_id`, `cid_id`, `houve_afastamento`, `houve_obito`, `leave_id` |
| `l10n_br.sst.cat`             | CAT                      | `acidente_id`, `tipo_cat_id`, `numero_recibo`, `date_emissao`, `esocial_evento_id`                                                                                                        |
| `l10n_br.sst.treinamento`     | Treinamento de NR        | `employee_id`, `treinamento_id` (Tab 29), `date`, `carga_horaria`, `date_reciclagem`, `responsavel`                                                                                       |

---

## 7. Critérios de aceite

1. Cadastrar PGR/LTCAT com riscos por ambiente e função e gerar **S-2240 em massa** para
   todos os trabalhadores afetados, com recibo do eSocial.
2. Registrar entrega de EPI com CA válido, assinatura eletrônica e baixa de estoque; a
   ficha em PDF reproduz o histórico completo.
3. Tentativa de entregar EPI com **CA vencido** é bloqueada.
4. ASO admissional obrigatório antes de ativar o contrato; periódicos agendados
   automaticamente pelo PCMSO; **S-2220** transmitido com recibo.
5. Acidente registrado gera **CAT dentro do prazo do 1º dia útil**, com alerta, e o
   afastamento correspondente via S-2230.
6. Trabalhador com exposição ensejadora de aposentadoria especial recebe **adicional
   GILRAT** na folha, com a alíquota correta (6/9/12%), refletido no S-1200.
7. Contrato marcado como insalubre **sem risco correspondente no laudo** dispara alerta
   de divergência.
8. Usuário do grupo RH **não** consegue acessar prontuário/dados clínicos.

---

## 8. Fases e sequência

| Fase  | Escopo                                 | Requisitos           | Resultado                                      |
| ----- | -------------------------------------- | -------------------- | ---------------------------------------------- |
| **0** | Destravar o eSocial + S-1005           | RS-01, RS-02         | Ciclo de eventos fecha; RAT/FAP disponíveis    |
| **1** | Base de riscos e laudos                | RS-03, RS-04         | Fonte única de risco                           |
| **2** | EPI (NR-6)                             | RS-05 a RS-08        | Ficha de EPI eletrônica válida em fiscalização |
| **3** | ASO/PCMSO (NR-7)                       | RS-09 a RS-11        | Controle de exames com bloqueios               |
| **4** | Acidentes e CAT                        | RS-12, RS-13         | Prazo legal atendido                           |
| **5** | Eventos SST no eSocial                 | RS-14 a RS-17        | **Conformidade eSocial SST**                   |
| **6** | Folha + sigilo                         | RS-18 a RS-20        | GILRAT correto e LGPD atendida                 |
| **7** | PGR, treinamentos, indicadores, portal | RS-21 a RS-30, RS-37 | Operação completa                              |
| **8** | CIPA, SESMT, integrações, painéis      | RS-31 a RS-36        | Produto maduro                                 |

**Ordem recomendada com as outras frentes:** a Fase 0 aqui (RS-01/RS-02) deveria ser
executada **junto com o RF-31** do PRD de folha — os dois precisam do S-1005 e das
alíquotas RAT/FAP. É o maior ganho de esforço compartilhado entre as três frentes.

---

## 9. Riscos e decisões em aberto

| #   | Risco / decisão                                                                            | Encaminhamento                                                                                                                                                                                |
| --- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | **RF-14 não corrigido** trava toda a frente SST                                            | Tratar como bloqueante da Fase 0, não como bug de backlog                                                                                                                                     |
| R2  | S-2240 tem alto volume (1 evento por trabalhador, com histórico)                           | Geração em lote via `queue_job` (OCA/queue) e reprocessamento; validar desempenho com 1.000+ vínculos                                                                                         |
| R3  | Dados de saúde sob LGPD art. 11 — vazamento tem consequência desproporcional               | Segregação de acesso desde a Fase 3, não depois                                                                                                                                               |
| R4  | Muitas empresas já usam sistema de SOC (clínica) e não vão migrar                          | Priorizar **importação** de ASO (RS-33) antes de sofisticar o cadastro próprio                                                                                                                |
| R5  | Erro no S-2240 prejudica a aposentadoria do trabalhador                                    | Validações pré-envio (RS-17) e trilha de auditoria de alteração de risco                                                                                                                      |
| R6  | Base da insalubridade (salário mínimo × piso) é controvertida                              | Parametrizar (RS-29) e submeter ao especialista fiscal                                                                                                                                        |
| D1  | **Decisão**: construir gestão de EPI própria ou adotar a pilha OCA?                        | Recomendação: adotar `hr_employee_ppe` + `hr_personal_equipment_stock` e só brasileirizar (§4.0/§4.2). O risco é herdar limitações do upstream — mitigável contribuindo as melhorias de volta |
| D2  | **Decisão**: o Odoo será a fonte do PGR/LTCAT ou apenas o consumidor do laudo de terceiro? | Recomendação: consumidor na Fase 1 (importar/anexar laudo), autoria depois                                                                                                                    |
| D3  | **Decisão**: bloquear ou apenas alertar em admissão sem ASO?                               | Configurável por empresa; padrão = alertar                                                                                                                                                    |

---

## 10. Lacunas de pesquisa (fazer antes de codificar)

1. **Leiaute oficial S-1.3 (NT 06/2026)** dos eventos S-1005, S-2210, S-2220, S-2221,
   S-2240 e S-2245 — campos, obrigatoriedades condicionais e regras de validação, direto
   do
   [portal de documentação técnica do eSocial](https://www.gov.br/esocial/pt-br/documentacao-tecnica).
2. Domínios oficiais do S-2220: `tpExameOcup` (confirmar nomenclatura do código 3 **e**
   o código do demissional — 9, não 8) e conferência da numeração de todas as tabelas de
   SST do repo contra o documento oficial "Tabelas do eSocial".
3. Regras de **prazo e retificação** de cada evento SST (o que exige S-3000).
4. Metodologia oficial do **FAP** para a simulação do RS-25.
5. Formatos de intercâmbio dos sistemas de **SOC** mais usados pela base de clientes
   (RS-33).
6. Texto vigente da **NR-6** quanto à assinatura eletrônica da ficha (verificar
   atualizações posteriores à Portaria SIT 107/2009).

---

## 11. Referências

**eSocial**

- [Documentação técnica oficial do eSocial](https://www.gov.br/esocial/pt-br/documentacao-tecnica)
- [Leiautes eSocial versão S-1.3 (NT 06/2026)](https://www.gov.br/esocial/pt-br/documentacao-tecnica/leiautes-esocial-versao-s-1-3-nt-06-2026-rev-09-04-2026/index.html)
- [Eventos SST S-2210, S-2220 e S-2240](https://dysonsst.com.br/blog/esocial-sst-eventos)
- [S-2240 — Condições Ambientais do Trabalho](https://www.sstonline.com.br/s-2240/)
- [S-2240 — codAgNoc e Tabela 24 (código 09.01.001)](https://suporte.senior.com.br/hc/pt-br/articles/4409388092564-HCM-S-2240-C%C3%B3digo-Agente-Nocivo-09-01-001-Tabela-24)
- [S-2221 — Exame Toxicológico do Motorista Profissional](https://documentacao.senior.com.br/gestao-de-pessoas-hcm/esocial/leiautes/nao-periodicos/s-2221.htm)
- [S-2221 — obrigatoriedade e prazos](https://www.rsdata.com.br/s-2221-exame-toxicologico-esocial-seguranca-trabalho/)
- [Manual SESI/SENAI — Eventos de SST no eSocial (2ª edição)](https://cronos-media.sesisenaisp.org.br/api/media/1-0/files?file=arq_67_221221_3c217e37-71ba-47e4-ad11-75656fcf8241.pdf&disposition=false)

**Normas e documentos de SST**

- [NR-6 — EPI: obrigações e cumprimento](https://sermst.com.br/normas/nr-06-epi)
- [Ficha de EPI digital e conformidade (Portaria SIT 107/2009)](https://www.migalhas.com.br/depeso/420104/ficha-de-epi-digital-e-conformidade-com-normas-de-seguranca)
- [Assinatura eletrônica em ficha de EPI](https://consultaca.com/blog/post/168/assinatura-eletronica-ou-digitalizada-em-ficha-de-epi-e-legal)
- [PGR, PCMSO, PPP e LTCAT — obrigações](https://www.asconnet.com/post/pgr-pcmso-ppp-e-ltcat-obriga%C3%A7%C3%A3o-trabalhista)
- [PPP eletrônico, LTCAT e eSocial — aposentadoria especial](https://sistemaeso.com.br/blog/esocial/guia-para-aposentadoria-especial-ppp-eletronico-ltcat-esocial)
- [PPP eletrônico obrigatório desde 2023 (Portaria MTP 334/2022)](https://www.contabeis.com.br/noticias/54044/ppp-eletronico-comecara-a-valer-em-2023/)

**Odoo / OCA (branches 16.0 verificadas)**

- [OCA/hr — hr_employee_ppe, hr_personal_equipment_request/\_stock/\_tier_validation, hr_employee_medical_examination](https://github.com/OCA/hr/tree/16.0)
- [OCA/management-system — mgmtsystem_hazard, \_nonconformity, \_action, \_health_safety](https://github.com/OCA/management-system/tree/16.0)
- [OCA/server-ux — base_tier_validation](https://github.com/OCA/server-ux/tree/16.0)
- [OCA/server-tools — auditlog, tracking_manager](https://github.com/OCA/server-tools/tree/16.0)
- [OCA/queue — queue_job](https://github.com/OCA/queue/tree/16.0)
- [OCA/reporting-engine — report_qweb_signer, report_py3o, report_xlsx](https://github.com/OCA/reporting-engine/tree/16.0)
- [OCA/data-protection — privacy, privacy_consent](https://github.com/OCA/data-protection/tree/16.0)
- [OCA/l10n-brazil — l10n_br_resource, l10n_br_fiscal_certificate](https://github.com/OCA/l10n-brazil/tree/16.0)

**Código analisado**

- `l10n_br_esocial/models/tabelas/esocial_tab_saude.py`, `esocial_tab_acidente.py`
- `l10n_br_esocial/models/intermediarios/` (inventário dos eventos implementados)
- `l10n_br_esocial/data/` (CSVs de tipo de ASO, tipo de CAT, agentes nocivos,
  financiamento de aposentadoria especial)
- `l10n_br_hr_payroll/models/hr_contract.py`, `data/hr_salary_rule_data.xml`
- `docs/PRD-folha-pagamento-evolucao.md` (RF-14, RF-25, RF-31)
