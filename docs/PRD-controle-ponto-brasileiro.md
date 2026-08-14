# PRD — Controle de Ponto Brasileiro (Portaria MTP 671/2021) para Odoo

**Status:** rascunho para revisão · **Data:** 2026-08-12 · **Repositório-alvo:**
[kmee/kmee-odoo-addons](https://github.com/kmee/kmee-odoo-addons) (branch `16.0`) ·
**Escopo:** registro de jornada aderente à legislação brasileira, integração com relógios
de ponto físicos (REP-C) e ligação com a folha de pagamento `l10n_br_hr_payroll`.

> Documento complementar ao [`docs/PRD-folha-pagamento-evolucao.md`](https://github.com/kmee/kmee-odoo-addons/blob/16.0/docs/PRD-folha-pagamento-evolucao.md).
> Aquele PRD trata do motor de cálculo da folha; **este trata da origem dos dados de
> jornada** que alimentam esse motor. Os códigos de requisito usam o prefixo `RP-`
> (Requisito Ponto) para não colidir com os `RF-` do PRD de folha.
>
> Itens marcados **[verificar]** dependem de conferência contra o texto oficial dos
> anexos da Portaria 671/2021 (leiautes byte a byte) — ver §11.

---

## 1. Contexto e problema

### 1.1 O que já existe no repositório

A frente de folha de pagamento está entregue: `l10n_br_hr_payroll` (INSS/IRRF/FGTS/verbas
CLT sobre o módulo OCA `payroll`), `l10n_br_hr_payroll_account`, `l10n_br_esocial`,
`l10n_br_hr_vacation`, `l10n_br_hr_benefit`, `l10n_br_hr_arquivos_governo`, entre outros.

Do lado de **jornada**, o repositório tem apenas dois módulos, ambos construídos sobre o
`hr_attendance` padrão do Odoo:

| Módulo | O que faz | Limitação |
| --- | --- | --- |
| `l10n_br_hr_overtime_custom_multiplier` | Multiplicador de HE por faixa/dia da semana/feriado sobre `hr.attendance.overtime`; wizard de "pagamento" de saldo; modelo `hr.attendance.exception` para sobrescrever o dia da semana | Nenhum vínculo com o holerite; bugs conhecidos (RF-11 a RF-13 do PRD de folha) |
| `hr_overtime_report_action_pdf` | Relatório PDF de horas extras | Relatório gerencial, não é espelho de ponto legal |

### 1.2 A integração ponto → folha **não existe**

Confirmado por leitura de código:

- `l10n_br_hr_payroll/models/hr_payslip.py:14-48` declara `l10n_br_horas_extras_50`,
  `l10n_br_horas_extras_100`, `l10n_br_horas_noturnas` e `l10n_br_faltas_injustificadas`
  como **campos editáveis manualmente no holerite**. Não há `compute`, nem `default`, nem
  qualquer leitura de `hr.attendance`.
- `hr_payslip.compute_sheet()` (`:51-69`) preenche `worked_days_line_ids` chamando
  `get_worked_day_lines()` do OCA `payroll`, que deriva os dias do **calendário de
  trabalho do contrato** (`resource.calendar`) e das ausências (`hr.leave`) — nunca das
  marcações reais.
- `hr_contract._l10n_br_horas_semanais()` (`:31-49`) lê `calendar.attendance_ids`, que são
  as **linhas de horário teórico** do `resource.calendar`, não marcações de ponto.
- `salary_rules_br.dias_trabalhados_mes()` (`:306-330`) calcula dias por **vigência
  contratual** (mês comercial de 30 dias), não por presença efetiva.

**Consequência prática:** hoje o RH digita horas extras, horas noturnas e faltas no
holerite. A folha está desacoplada da realidade fática da jornada — exatamente o que a
fiscalização e a Justiça do Trabalho cobram.

### 1.3 O que a legislação exige e não está coberto

Nada no repositório gera **AFD**, **AEJ**, **espelho de ponto** ou **comprovante de
registro**; não há NSR, imutabilidade de marcação, assinatura ICP-Brasil, nem importação
de arquivos de relógio físico. O `hr_attendance` padrão do Odoo, sozinho, **viola** a
Portaria 671 em pontos estruturais (marcações editáveis sem trilha, sem NSR, sem
comprovante, sem arquivo fiscal).

### 1.4 Problema a resolver

> Fazer o Odoo apurar a jornada de trabalho de forma aderente à legislação brasileira —
> tanto quando o registro nasce **no próprio Odoo** (ponto digital) quanto quando nasce
> em **relógios físicos de terceiros** (REP-C) — e alimentar automaticamente a folha de
> pagamento com dias trabalhados, faltas, DSR, horas extras por faixa, adicional noturno
> e banco de horas.

---

## 2. Marco legal (pesquisa)

### 2.1 CLT — regras materiais de jornada

| Dispositivo | Regra | Impacto no sistema |
| --- | --- | --- |
| Art. 58 | Jornada normal 8h/dia, 44h/semana | Parâmetro do contrato/calendário |
| Art. 58, §1º | **Tolerância**: variações de até 5 min por marcação, limitadas a **10 min/dia**, não são hora extra (Súmula 366 TST: ultrapassado o limite, computa-se o tempo **integral**) | Motor de apuração: regra "tudo ou nada", não é desconto de franquia |
| Art. 58, §2º | Tempo de deslocamento não é jornada (pós-reforma) | Não modelar horas *in itinere* por padrão |
| Art. 59 | Até 2h extras/dia; **banco de horas** por acordo individual (compensação em até **6 meses**) ou coletivo (até **12 meses**) | Banco de horas com data-limite e expurgo |
| Art. 59-A | Escala **12x36** por acordo individual escrito | Calendário de 2 semanas + regras próprias de DSR/feriado |
| Art. 62, I–III | Excluídos do controle: atividade externa incompatível, cargo de gestão, **teletrabalho por produção/tarefa** | Flag por contrato: "dispensado de controle de jornada" |
| Art. 66 | Intervalo **interjornada** mínimo de 11h | Validação/ocorrência na apuração |
| Art. 67 | Repouso semanal remunerado (DSR) de 24h, preferencialmente domingo | Desconto de DSR por falta injustificada |
| Art. 71 | Intervalo **intrajornada**: mín. 1h (máx. 2h) para jornadas > 6h; 15 min para jornadas de 4h a 6h. **Art. 611-A, III**: negociação coletiva pode reduzir o mínimo até **30 min** | Validação obrigatória, com **mínimo parametrizável por CCT/ACT** |
| Art. 71, §4º | Supressão/redução do intervalo → pagar **apenas o período suprimido** com +50%, natureza **indenizatória** (pós-reforma) | Rubrica própria, fora da base INSS/IRRF |
| Art. 73 | Adicional noturno urbano ≥ 20%, das **22h às 5h**, com **hora reduzida de 52min30s** | Já há campo `l10n_br_usar_hora_reduzida` no holerite, sem fonte de dados |
| Art. 74, §2º (red. Lei 13.874/2019) | Obrigatório registro de jornada em estabelecimentos com **mais de 20 trabalhadores** | Regra de obrigatoriedade por estabelecimento |
| Art. 74, §4º | Admitido o registro **por exceção**, mediante acordo individual escrito, convenção ou acordo coletivo | Modo de operação alternativo do módulo |

**Jurisprudência relevante:** Súmula 338 TST (não apresentação injustificada dos controles
gera presunção relativa da jornada alegada pelo empregado; horários "britânicos"/uniformes
são inválidos como prova) e Súmula 366 TST (tolerância).

### 2.2 Portaria MTP nº 671/2021 — o regulamento do ponto eletrônico

Publicada em 08/11/2021, consolidou e **revogou** as Portarias 1.510/2009 e 373/2011.
O capítulo de registro eletrônico de ponto vai dos arts. 73 a 101.

**Os três sistemas (art. 75 — o empregador deve usar um deles):**

| Tipo | Base legal | Natureza | Requisito de habilitação |
| --- | --- | --- | --- |
| **REP-C** (Convencional) | Art. 76 | Equipamento físico monolítico, com nº de fabricação, uso exclusivo para jornada | Certificação INMETRO (Anexo VIII / Portaria INMETRO 4/2022) + homologação publicada no DOU |
| **REP-A** (Alternativo) | Art. 77 | Conjunto de equipamentos e programas | **Exige autorização por convenção ou acordo coletivo** |
| **REP-P** (via Programa) | Art. 78 | *Software* em servidor dedicado ou nuvem, uso exclusivo para registro de jornada | **Registro do programa no INPI** + atendimento ao **Anexo IX**; não exige acordo coletivo |

**Vedações (art. 74)** — aplicáveis a qualquer sistema:

- restrições de horário à marcação de ponto;
- marcação automática com horários predeterminados (o "ponto britânico");
- exigência de autorização prévia para marcação de sobrejornada;
- **quaisquer dispositivos que permitam alteração dos registros originais**.

**Artefatos obrigatórios:**

| Artefato | Base | Quem gera | Conteúdo |
| --- | --- | --- | --- |
| **Comprovante de registro de ponto** | Arts. 79–80 | O REP | Identificação de empregador e trabalhador, data/hora, **NSR**, identificação do REP, local da prestação, **código hash** (REP-P), assinatura eletrônica. Acesso eletrônico após cada marcação e **extração das últimas 48 horas** |
| **AFD — Arquivo Fonte de Dados** | Art. 81, Anexo V | Somente o REP | Marcações brutas, **imutáveis**; texto ASCII/ISO-8859-1, campos separados por `\|`, linhas em CRLF, **NSR sequencial sem lacunas por estabelecimento (CNPJ/CPF), iniciando em 1**; validação **CRC-16 CCITT-TRUE** e assinatura **CAdES** em `.p7s` destacado **[verificar]** |
| **AEJ — Arquivo Eletrônico de Jornada** | Arts. 82–83, Anexo VI | O **PTRP** (Programa de Tratamento de Registro de Ponto) | Substituiu AFDT e ACJEF. Contém vínculos, horário contratual, marcações tratadas, ausências e banco de horas. Assinado pelo desenvolvedor do PTRP (CAdES). Data-hora com **fuso obrigatório** (`AAAA-MM-ddThh:mm:00ZZZZZ`); `durJornada` em **minutos** |
| **Espelho de Ponto Eletrônico** | Arts. 82–84 | O PTRP | Identificação, período, **jornada contratual**, marcações (inclusive as de intervalo intrajornada), duração das jornadas |
| **Atestado Técnico e Termo de Responsabilidade** | Art. 89, Anexo VII | Fabricante (REP-C) / desenvolvedor (REP-A, REP-P) | Documento eletrônico com assinatura **qualificada ICP-Brasil** (A1 ou A3) de responsável legal **e** técnico. O empregador só pode usar sistema com atestado válido (§4º) |

**Leiaute do AFD (Anexo V) — tipos de registro** *[verificar campos]*:

| Tipo | Conteúdo |
| --- | --- |
| 1 | Cabeçalho |
| 2 | Inclusão/alteração de identificação do empregador no REP |
| 3 | Marcação de ponto (REP-C e REP-A) |
| 4 | Ajuste do relógio |
| 5 | Inclusão/alteração/exclusão de empregado no REP |
| 6 | Eventos sensíveis do REP |
| **7** | **Marcação de ponto do REP-P** |
| 9 | *Trailer* |
| — | Bloco de assinatura digital |

**Leiaute do AEJ (Anexo VI) — tipos de registro** *[verificar campos]*:

| Tipo | Conteúdo |
| --- | --- |
| 01 | Cabeçalho |
| 02 | REPs utilizados |
| 03 | Vínculos (contratos) |
| 04 | Horário contratual (`durJornada` em minutos) |
| 05 | Marcações de ponto tratadas |
| 06 | Identificação eSocial do trabalhador (múltiplos vínculos) |
| 07 | Ausências e banco de horas |
| 08 | Identificação do PTRP |
| 99 | *Trailer* |

**Demais obrigações:**

- **Art. 82** — o PTRP pode **apenas** complementar omissões e indicar marcações
  indevidas; **não pode alterar** o dado de origem. Toda correção é rastreável e vive no
  AEJ/espelho, nunca no AFD.
- **Art. 85** — o empregador deve fornecer arquivos e relatórios ao Auditor-Fiscal em
  prazo mínimo de 2 dias.
- **Arts. 86–88** — assinatura eletrônica conforme MP 2.200-2/2001; REP-A, REP-P e o PTRP
  usam **certificado ICP-Brasil** (assinatura qualificada, Lei 14.063/2020). PDFs
  (comprovante do REP-P) em **PAdES**; arquivos em **CAdES**.
- **Art. 98** — adulteração de horários autoriza apreensão de equipamentos e cópia de
  dados.
- **Art. 101** — observância obrigatória da **LGPD** (Lei 13.709/2018).
- Marcações devem ser **fidedignas à realidade fática** e as jornadas devem ter **número
  par de marcações**; as marcações de intervalo intrajornada (art. 74, §2º CLT) **devem
  constar** do AEJ e do espelho de ponto.
- **Guarda:** não há prazo único na Portaria; a prática de mercado é reter AFD/AEJ/espelho
  por **no mínimo 5 anos** (prescrição trabalhista, art. 7º, XXIX, CF) — recomendado 10.

### 2.3 Consequência de arquitetura

Os dois papéis da Portaria são **separáveis** e é isso que define o produto:

- **REP** — quem *captura* a marcação e gera o AFD imutável. Pode ser um relógio físico de
  terceiro (REP-C) ou o próprio Odoo (REP-P).
- **PTRP** — quem *trata* as marcações e gera AEJ e espelho de ponto. **Sempre é o Odoo**,
  em qualquer cenário.

Isso permite entregar valor em fases: primeiro o PTRP (que serve inclusive a quem usa
relógio físico de outro fabricante), depois o REP-P.

---

## 3. Objetivos e não-objetivos

### Objetivos

1. **PTRP completo**: apurar jornada a partir de marcações (próprias ou importadas), com
   tolerância, intervalos, adicional noturno, HE por faixa, DSR e banco de horas, e gerar
   **AEJ + espelho de ponto** assinados.
2. **Integração com relógios físicos**: importar AFD de REP-C de qualquer fabricante e
   conciliar por PIS/CPF, com detecção de lacunas de NSR.
3. **Ponto digital aderente**: marcação no Odoo (web/portal/app) com NSR, imutabilidade,
   comprovante e janela de 48h — pavimentando o caminho para o **REP-P**.
4. **Alimentar a folha automaticamente**: eliminar a digitação manual de HE, horas
   noturnas e faltas no holerite; derivar `worked_days` de presença efetiva.
5. **Trilha de auditoria completa**: AFD imutável, correções sempre rastreáveis, aderentes
   ao art. 82.

### Não-objetivos (desta fase)

- Fabricar/certificar hardware REP-C (Anexo VIII / INMETRO).
- Buscar autorização de REP-A (depende de negociação coletiva do cliente).
- Reconhecimento facial/biometria própria (usar o que o REP-C do cliente já faz; se
  necessário, integrar via SDK do fabricante em módulo separado).
- Aplicativo móvel nativo (fase posterior; PWA/portal atende o piloto).
- Cobertura de convenções coletivas específicas por categoria.

---

## 4. Decisão estratégica: qual papel a KMEE assume

Três caminhos, com custo regulatório crescente. **Recomendação: A → B, nesta ordem.**

| | **A. PTRP + importador de AFD** | **B. REP-P (Odoo é o registrador)** | **C. REP-A** |
| --- | --- | --- | --- |
| O que é | Odoo trata marcações vindas de relógios de terceiros | Odoo captura a marcação e gera o AFD | Conjunto misto autorizado por norma coletiva |
| Custo regulatório | **Baixo** — atestado técnico do PTRP (art. 89) | **Médio** — registro no INPI + Anexo IX + atestado + assinatura ICP-Brasil | Alto — depende de acordo coletivo do cliente |
| Hardware | Do cliente (qualquer fabricante) | Nenhum | Variável |
| Atende ao pedido "integrar com controle de ponto físico" | **Sim, integralmente** | Não (substitui) | Parcialmente |
| Habilita ponto 100% digital | Não | **Sim** | Sim |
| Risco | Baixo | Médio (conformidade do Anexo IX) | Alto (comercial) |

**Justificativa da sequência:** a Fase A já resolve o problema imediato do cliente (a folha
não enxerga a jornada) e serve a **todo** cliente que já tem relógio instalado — a maioria.
O AEJ e o espelho de ponto são obrigatórios nos dois cenários, então o investimento é
100% reaproveitado. A Fase B só adiciona a camada de captura e a burocracia de INPI.

No roadmap do §9, o caminho **A** corresponde às fases 1–4 e o caminho **B** à fase 5.

---

## 5. Arquitetura de módulos proposta

```
hr_attendance (Odoo core)
   └── l10n_br_hr_attendance ................. base: NSR, marcação imutável, tipos, estabelecimento
        ├── l10n_br_hr_attendance_afd ........ import/export AFD (Anexo V) + CRC-16 + drivers de REP-C
        ├── l10n_br_hr_attendance_apuracao ... motor: tolerância, intrajornada, noturno, HE, DSR, ocorrências
        │    ├── l10n_br_hr_attendance_aej ... AEJ (Anexo VI) + Espelho de Ponto
        │    ├── l10n_br_hr_attendance_banco_horas ... banco de horas com prazo e expurgo
        │    └── l10n_br_hr_payroll_attendance ...... PONTE ponto → holerite
        └── l10n_br_hr_attendance_rep_p ...... comprovante, hash, janela 48h, portal do empregado
             └── l10n_br_hr_attendance_signature ... ICP-Brasil CAdES/PAdES (erpbrasil.assinatura)
```

### 5.0 Reuso de módulos OCA (verificado na 16.0)

| Módulo OCA (16.0) | Repo | O que resolve aqui |
| --- | --- | --- |
| **`l10n_br_resource`** | OCA/l10n-brazil | Calendário brasileiro com **feriados** (via `workalendar`) e cálculo de dias úteis. Resolve a limitação **já documentada no código** (`salary_rules_br.py:175-179`: "feriados NÃO são computados como DSR… ver `l10n_br_resource`") — vale para o DSR da apuração (RP-14) e para o **RF-26** do PRD de folha |
| **`hr_attendance_report_theoretical_time`** | OCA/hr-attendance | Compara **tempo teórico × tempo efetivo** — é o esqueleto do motor de apuração diária (RP-09), poupando a modelagem do confronto jornada prevista × realizada |
| **`hr_attendance_autoclose`** | OCA/hr-attendance | Fecha marcações abertas (entrada sem saída) — apoia a validação de **paridade** exigida pela Portaria (RP-09), embora o fechamento automático precise virar **ocorrência**, nunca marcação fabricada (art. 74) |
| **`hr_attendance_reason`** | OCA/hr-attendance | Motivo da marcação — base para a tipificação de ocorrências do AEJ |
| **`hr_attendance_modification_tracking`** | OCA/hr-attendance | Registra alterações de marcação no chatter — ponto de partida do RP-03, que ainda precisa ser **mais forte** (bloquear a alteração, não só registrá-la) |
| **`hr_attendance_geolocation`** | OCA/hr-attendance | Geolocalização no check-in/out — útil no REP-P móvel (não é exigência da Portaria, mas é prática de mercado) |
| **`hr_attendance_rfid`** | OCA/hr-attendance | Marcação por RFID/crachá — caminho alternativo de captura para catracas |
| **`hr_attendance_calendar_view`** | OCA/hr-attendance | Visão de calendário das marcações — reduz UI própria no espelho de ponto |
| **`auditlog`** | OCA/server-tools | Trilha de auditoria por modelo/campo — sustenta a imutabilidade e a rastreabilidade do art. 82 |
| **`queue_job`** | OCA/queue | Importação de AFD em massa e apuração em fila (RP-40) |
| **`report_qweb_signer`** | OCA/reporting-engine | **Assina PDF com certificado PKCS#12** — entrega o **PAdES** do comprovante de registro (RP-26) e do espelho de ponto sem escrever camada de assinatura |
| **`l10n_br_fiscal_certificate`** | OCA/l10n-brazil | Gestão de **certificado A1** (armazenamento, validade, alertas) — reusar em vez de criar cadastro próprio para RP-22/RP-28 |
| **`base_tier_validation`** | OCA/server-ux | Aprovação em camadas — fluxo de solicitação de ajuste de ponto pela chefia (RP-31); já presente na *stack* do repo |
| **`hr_holidays_public`** | OCA/hr-holidays | Feriados públicos — já consumido pelo `l10n_br_hr_holidays_public` do repo |
| **`report_py3o` / `report_xlsx`** | OCA/reporting-engine | Espelho de ponto e relatórios; `report_py3o` **já é usado no repo** |

**Ressalva importante:** nenhum módulo OCA de *attendance* é aderente à Portaria 671 —
não há NSR, AFD, AEJ, comprovante nem imutabilidade. Eles encurtam a **infraestrutura**
(captura, visualização, comparação teórico × real, trilha), não a **conformidade legal**,
que continua sendo trabalho novo.

### 5.1 `l10n_br_hr_attendance` (base)

Fundação comum. Estende `hr.attendance` com o que a Portaria exige de **toda** marcação:

- `l10n_br_nsr` (Integer, sequencial **por estabelecimento**, sem lacunas, inicia em 1);
- `l10n_br_origem` (Selection: `rep_c`, `rep_a`, `rep_p`, `importacao`, `tratamento`);
- `l10n_br_rep_id` (M2O para `l10n_br.hr.rep` — cadastro do registrador: tipo, nº de
  fabricação, modelo, CNPJ do estabelecimento, INPI/INMETRO, atestado técnico);
- `l10n_br_tipo_marcacao` (entrada/saída — a paridade é obrigatória);
- `l10n_br_hash` e `l10n_br_assinatura` (quando REP-P);
- **imutabilidade**: `write`/`unlink` bloqueados para marcações originais; qualquer
  correção nasce como registro de **tratamento** vinculado ao original (art. 82).

Estende `res.company`/`hr.employee`/`hr.contract`:

- estabelecimento (CNPJ) da marcação, para o NSR e para o AFD;
- `l10n_br_dispensado_controle_jornada` (art. 62 CLT) e `l10n_br_registro_por_excecao`
  (art. 74, §4º) no contrato;
- PIS/PASEP e CPF do empregado (já presentes em `l10n_br_hr`) como chave de conciliação.

### 5.2 `l10n_br_hr_attendance_afd`

- **Importação** de AFD (Anexo V, tipos 1–9): parser posicional, validação de CRC-16 e de
  sequência de NSR, detecção de lacunas e de arquivos duplicados, conciliação por
  PIS/CPF, relatório de importação com linhas rejeitadas.
- **Exportação** de AFD quando o Odoo for o REP (Fase B).
- Suporte ao leiaute **antigo (Portaria 1.510/2009)**, ainda gerado por REP-C certificados
  antes de 10/02/2022 (art. 96) — obrigatório na prática.
- **Drivers de coleta** por fabricante em submódulos (`..._afd_control_id`,
  `..._afd_henry`, `..._afd_topdata`, `..._afd_madis`, `..._afd_dimep`): coleta por
  pasta/FTP/HTTP/pen drive. O núcleo trata só do arquivo; o driver trata do transporte.

### 5.3 `l10n_br_hr_attendance_apuracao` (o coração)

Modelo `l10n_br.hr.apuracao.dia` (uma linha por empregado/dia), com:

- jornada contratual do dia (do `resource.calendar`, com exceções e feriados via
  `l10n_br_hr_holidays_public`);
- marcações do dia, pareadas (validação de paridade);
- **tolerância** art. 58 §1º: 5 min por marcação / 10 min por dia, regra "tudo ou nada"
  (Súmula 366);
- **intrajornada**: verificação do mínimo legal — parametrizável, pois CCT/ACT pode
  reduzi-lo até 30 min (art. 611-A, III) — e cálculo do período suprimido (art. 71, §4º)
  como verba indenizatória;
- **interjornada**: ocorrência quando < 11h (art. 66) — entregue como RP-33 (P1);
- **adicional noturno**: interseção com 22h–5h, com hora reduzida de 52min30s;
- **horas extras por faixa**, reaproveitando `hr.overtime.multiplier.range` do
  `l10n_br_hr_overtime_custom_multiplier` (após corrigir RF-11/RF-12/RF-13);
- **faltas** (injustificadas, justificadas, atrasos) e reflexo em **DSR**;
- **ocorrências** tipificadas para o AEJ (falta, abono, atestado, feriado, compensação);
- fechamento por competência, com trava: **período fechado não recalcula**.

### 5.4 `l10n_br_hr_attendance_aej`

Gera o **AEJ** (Anexo VI, registros 01–08 e 99) e o **Espelho de Ponto** (art. 84) em PDF,
a partir da apuração fechada. Assina via `l10n_br_hr_attendance_signature`. Armazena os
arquivos com retenção configurável (padrão 5 anos) e disponibiliza *download* rápido para
atendimento ao Auditor-Fiscal dentro do prazo do art. 85.

### 5.5 `l10n_br_hr_payroll_attendance` (a ponte pedida)

O módulo que fecha o *gap* apontado em §1.2. Substitui a digitação manual por `compute`
com `readonly=False` (mantém a possibilidade de sobrescrita justificada) em
`hr.payslip`:

| Campo do holerite | Passa a ser derivado de |
| --- | --- |
| `l10n_br_horas_extras_50` | Soma das HE apuradas na faixa 50% |
| `l10n_br_horas_extras_100` | Soma das HE apuradas na faixa 100% |
| `l10n_br_horas_noturnas` | Interseção 22h–5h apurada |
| `l10n_br_faltas_injustificadas` | Contagem de faltas injustificadas |
| `worked_days_line_ids` | Dias de presença efetiva + ausências tipificadas (override de `get_worked_day_lines`) |

Acrescenta rubricas hoje inexistentes: **DSR sobre horas extras** (Lei 605/49, Súmula 172
TST), **intervalo suprimido** (art. 71 §4º, indenizatório) e **desconto de DSR por falta**.
Publica no `localdict` do motor de regras (`_get_tools_dict`) os totais da apuração, para
que regras salariais possam consumi-los sem acoplamento.

### 5.6 `l10n_br_hr_attendance_banco_horas`

Saldo por empregado com **data-limite** (6 meses para acordo individual, 12 para coletivo —
art. 59), política de compensação (1:1 ou com multiplicador), expurgo automático no
vencimento com conversão em HE paga, e extrato para o registro 07 do AEJ. Substitui o
wizard de "pagamento" atual, que só cria um lançamento negativo solto.

### 5.7 `l10n_br_hr_attendance_rep_p` + `_signature`

- Marcação pelo empregado (web/portal/quiosque) **sem restrição de horário** e **sem
  autorização prévia** (art. 74);
- geração de **NSR**, **hash** e comprovante em **PDF assinado (PAdES)**;
- portal do empregado com acesso ao comprovante e extração das **últimas 48 horas**
  (art. 80, parágrafo único);
- geração e assinatura do **AFD** (CAdES/`.p7s`);
- `_signature` encapsula ICP-Brasil (A1/A3) reaproveitando `erpbrasil.assinatura`, já usada
  na localização fiscal — evita nova dependência.

---

## 6. Requisitos priorizados

### P0 — MVP: PTRP + relógio físico + folha (bloqueiam o uso real)

**Base**

- **RP-01** — Cadastro `l10n_br.hr.rep` (tipo C/A/P, nº de fabricação, modelo,
  certificação INMETRO ou INPI, CNPJ do estabelecimento, vigência do atestado técnico).
- **RP-02** — NSR sequencial por estabelecimento, sem lacunas, iniciando em 1, com
  *constraint* de unicidade e sequência transacionalmente segura.
- **RP-03** — Imutabilidade da marcação de origem: bloquear `write`/`unlink`; toda
  correção gera registro de tratamento vinculado, com autor, data e motivo (art. 82).
- **RP-04** — Flags de contrato: dispensa de controle (art. 62) e registro por exceção
  (art. 74, §4º).

**AFD / relógio físico**

- **RP-05** — Importador de AFD no leiaute da **Portaria 671 (Anexo V)**, tipos 1–9, com
  validação de CRC-16 e verificação de continuidade de NSR.
- **RP-06** — Importador de AFD no leiaute **legado (Portaria 1.510/2009)** — REP-C
  certificados antes de 10/02/2022 continuam legais (art. 96) e são a base instalada.
- **RP-07** — Conciliação por PIS/PASEP com *fallback* para CPF; fila de pendências para
  marcações sem empregado correspondente (nunca descartar silenciosamente).
- **RP-08** — Idempotência: reimportar o mesmo AFD não duplica marcações; detecção de
  lacuna de NSR gera alerta bloqueante no fechamento.

**Apuração**

- **RP-09** — Motor diário de apuração com pareamento de marcações e validação de
  paridade.
- **RP-10** — Tolerância art. 58 §1º (5 min/marcação, 10 min/dia, regra "tudo ou nada").
- **RP-11** — Intervalo intrajornada: validação do mínimo e cálculo do período suprimido
  (art. 71 §4º) como verba **indenizatória**.
- **RP-12** — Adicional noturno 22h–5h com hora reduzida de 52min30s (alimenta
  `l10n_br_usar_hora_reduzida`, hoje sem fonte).
- **RP-13** — HE por faixa/dia da semana/feriado reaproveitando
  `hr.overtime.multiplier.range` — **depende de corrigir RF-11, RF-12 e RF-13 do PRD de
  folha** (crash em múltiplas faixas, bug de *locale* no dia da semana, ACL permissiva).
- **RP-14** — Faltas, atrasos e reflexo em DSR.
- **RP-15** — Fechamento de competência com trava contra recálculo.

**Ponte com a folha**

- **RP-16** — `compute` (com `readonly=False`) dos quatro campos manuais do holerite a
  partir da apuração fechada.
- **RP-17** — `get_worked_day_lines` derivado de presença efetiva, preservando o
  comportamento atual como *fallback* quando não houver apuração (compatibilidade com os
  testes existentes de `test_worked_days.py`).
- **RP-18** — Rubricas novas: **DSR sobre HE** (Súmula 172 TST), **intervalo suprimido**,
  **desconto de DSR por falta**.
- **RP-19** — Divergência apuração × holerite bloqueia a validação do holerite (ou exige
  justificativa registrada).

**Artefatos legais**

- **RP-20** — Geração do **AEJ** (Anexo VI, registros 01–08 e 99).
- **RP-21** — **Espelho de Ponto** (art. 84) em PDF, com jornada contratual, todas as
  marcações (inclusive intrajornada) e duração das jornadas.
- **RP-22** — Assinatura **CAdES** (`.p7s` destacado) do AEJ com certificado ICP-Brasil
  (A1/A3) da KMEE como desenvolvedora do PTRP, reusando `l10n_br_fiscal_certificate` para
  a gestão do certificado e `erpbrasil.assinatura` para a assinatura.
- **RP-23** — Retenção e *download* dos arquivos por competência, com prazo padrão de 5
  anos, para atendimento do art. 85.
- **RP-24** — **Atestado Técnico e Termo de Responsabilidade do PTRP** (art. 89, Anexo
  VII) — entregável **jurídico/documental**, não de código, mas bloqueante para o uso do
  sistema pelo cliente (§4º).

### P1 — REP-P e completude operacional

- **RP-25** — Marcação no Odoo (portal/quiosque) sem restrição de horário nem autorização
  prévia (art. 74).
- **RP-26** — Comprovante de registro (art. 79) em PDF **PAdES**, com NSR e hash, via
  `report_qweb_signer` (OCA/reporting-engine).
- **RP-27** — Janela de **48 horas** de extração de comprovantes pelo empregado (art. 80).
- **RP-28** — Geração e assinatura do **AFD** pelo Odoo (REP-P).
- **RP-29** — **Registro do programa no INPI** e conformidade com o **Anexo IX**
  (entregável regulatório).
- **RP-30** — Banco de horas com prazo (6/12 meses), política de compensação e expurgo
  automático no vencimento.
- **RP-31** — Portal do empregado: espelho de ponto, saldo de banco de horas, solicitação
  de ajuste com aprovação da chefia (o ajuste vira registro de tratamento, nunca altera o
  original).
- **RP-32** — Escala **12x36** (art. 59-A) e jornadas especiais.
- **RP-33** — Interjornada de 11h (art. 66) como ocorrência.
- **RP-34** — Drivers de coleta por fabricante (Control iD, Henry, Topdata, Madis, Dimep).
- **RP-35** — Alinhamento com o **eSocial**: o horário contratual do `resource.calendar`
  alimenta simultaneamente o registro 04 do AEJ e o grupo `horContratual` do S-2200/S-2206
  em `l10n_br_esocial` — fonte única, sem duplicidade de cadastro.

### P2 — qualidade, LGPD e higiene

- **RP-36** — **LGPD** (art. 101): base legal por finalidade (obrigação legal), política
  de retenção e descarte, minimização (não armazenar template biométrico no Odoo —
  referenciar o ID do dispositivo), *log* de acesso a dados de jornada.
- **RP-37** — Perfis de acesso: empregado (só os próprios dados), gestor (equipe), RH
  (tudo), auditor (somente leitura, com trilha de acesso).
- **RP-38** — Detecção de "ponto britânico" (marcações uniformes) como alerta interno —
  risco direto sob a Súmula 338 TST.
- **RP-39** — Painel de conformidade por estabelecimento: obrigatoriedade (> 20
  empregados), atestado técnico vigente, competências fechadas, arquivos gerados.
- **RP-40** — Importação em massa e desempenho: AFD anual de 300 empregados ≈ 250 mil
  marcações — importação em lote e apuração em fila.
- **RP-41** — Cobertura de testes com **AFDs reais** de cada fabricante como fixtures.

---

## 7. Modelo de dados (esboço)

| Modelo | Papel | Campos-chave |
| --- | --- | --- |
| `l10n_br.hr.rep` | Cadastro do registrador | `tipo` (C/A/P), `numero_fabricacao`, `modelo`, `inmetro`/`inpi`, `company_id`, `cnpj_estabelecimento`, `atestado_*`, `nsr_atual` |
| `hr.attendance` (herda) | Marcação | `l10n_br_nsr`, `l10n_br_rep_id`, `l10n_br_origem`, `l10n_br_tipo_marcacao`, `l10n_br_hash`, `l10n_br_marcacao_origem_id` |
| `l10n_br.hr.afd.import` | Lote de importação | `arquivo`, `rep_id`, `nsr_inicial`/`nsr_final`, `state`, `linhas_ok`/`rejeitadas`, `hash_arquivo` |
| `l10n_br.hr.apuracao.dia` | Apuração diária | `employee_id`, `date`, `jornada_prevista`, `jornada_realizada`, `he_50`, `he_100`, `noturnas`, `atraso`, `falta`, `intrajornada_suprimida`, `banco_horas_delta`, `ocorrencia_ids` |
| `l10n_br.hr.apuracao.periodo` | Fechamento | `date_from`/`date_to`, `company_id`, `state` (aberto/fechado), `aej_file`, `aej_p7s`, `espelho_pdf` |
| `l10n_br.hr.banco.horas` | Saldo | `employee_id`, `saldo`, `data_limite`, `politica`, `movimento_ids` |
| `l10n_br.hr.ocorrencia` | Tipificação | `codigo` (mapeado para o AEJ), `descricao`, `desconta_dsr`, `abona` |

---

## 8. Critérios de aceite

1. Importar um AFD real de REP-C (leiautes 671 **e** 1.510) de 12 meses sem perda de
   marcação, com relatório de lacunas de NSR.
2. Fechar uma competência e gerar **AEJ assinado** que passe em validador de terceiro
   **[verificar disponibilidade de validador oficial]**.
3. Espelho de ponto contendo jornada contratual, todas as marcações e duração diária,
   conferindo com o AFD de origem.
4. Holerite calculado **sem digitação manual** de HE, noturnas ou faltas, com valores
   idênticos aos de uma conferência manual em planilha para 3 cenários (jornada padrão,
   12x36, mês com falta + feriado).
5. Tentativa de editar marcação de origem **falha** e gera registro de tratamento.
6. Marcação fora do horário previsto é **aceita** (art. 74) e aparece na apuração.
7. Empregado extrai comprovante das últimas 48h pelo portal (fase 5 — REP-P).
8. Reimportação do mesmo AFD não gera duplicidade.

---

## 9. Fases e sequência

| Fase | Escopo | Requisitos | Resultado |
| --- | --- | --- | --- |
| **0** | Correções bloqueantes no módulo de HE existente | RF-11, RF-12, RF-13 (PRD de folha) | Base de HE confiável |
| **1** | Base + importação de AFD | RP-01 a RP-08 | Odoo enxerga o relógio físico |
| **2** | Motor de apuração | RP-09 a RP-15 | Jornada apurada conforme CLT |
| **3** | Ponte com a folha | RP-16 a RP-19 | **Fim da digitação manual — resolve a dor imediata** |
| **4** | AEJ + espelho + assinatura + atestado | RP-20 a RP-24 | **Conformidade como PTRP** |
| **5** | REP-P | RP-25 a RP-29 | Ponto 100% digital no Odoo |
| **6** | Banco de horas, portal, escalas, drivers | RP-30 a RP-35 | Operação completa |
| **7** | LGPD, segurança, desempenho, painéis | RP-36 a RP-41 | Produto maduro |

As fases 1–3 já entregam o valor pedido ("pegar os dias trabalhados do controle de
entrada e saída para a folha"). A fase 4 é o que torna o uso **legalmente defensável**.

---

## 10. Riscos e decisões em aberto

| # | Risco / decisão | Encaminhamento |
| --- | --- | --- |
| R1 | **Atestado Técnico do PTRP (art. 89)** exige responsável legal e técnico pessoa física com certificado ICP-Brasil. Sem ele o cliente não pode usar o sistema (§4º) | Definir os responsáveis na KMEE **antes** da fase 4 — é caminho crítico, não detalhe |
| R2 | Leiautes dos Anexos V/VI não foram obtidos byte a byte nesta pesquisa | Extrair do PDF oficial do DOU antes de codificar (§11) |
| R3 | Registro no INPI (REP-P) tem prazo próprio | Iniciar o processo em paralelo à fase 4, não na fase 5 |
| R4 | Módulo AGPL vs. exclusividade do REP-P — o código é publicável, mas o **atestado** é da KMEE | Confirmar que licença aberta não conflita com a responsabilização do desenvolvedor |
| R5 | Base instalada de REP-C com leiaute antigo | Suportar os dois leiautes desde a fase 1 (RP-06) |
| R6 | Divergência entre convenções coletivas e o motor genérico | Parametrizar tolerância, faixas de HE e adicional noturno por sindicato, reusando `l10n_br_hr_syndicate` |
| R7 | `hr_attendance` do Odoo assume um par check-in/check-out por sessão; intrajornada exige múltiplos pares/dia | Validar cedo se o modelo core comporta ou se é preciso um modelo de marcação próprio |
| R8 | Volume de dados | RP-40; definir estratégia de arquivamento |
| D1 | **Decisão**: assumir REP-P ou ficar só no PTRP? | Recomendação: PTRP primeiro (fases 1–4), REP-P depois, conforme demanda comercial |
| D2 | **Decisão**: contribuir para OCA (`l10n-brazil`/`hr-attendance`) ou manter em `kmee-odoo-addons`? | Incubar aqui, migrar depois — mesma política dos demais módulos |

---

## 11. Lacunas de pesquisa (fazer antes de codificar)

1. **Anexos V e VI em PDF oficial** — posições, tamanhos e tipos de cada campo de cada
   registro; regra exata de cálculo do CRC-16 CCITT-TRUE e onde ele entra.
2. **Anexo IX** — lista fechada de requisitos técnicos do REP-P (necessária para a fase 5).
3. **Anexo VII** — modelo exato do Atestado Técnico.
4. Existência de **validador oficial** de AFD/AEJ para os testes de aceite.
5. Amostras reais de AFD dos fabricantes mais comuns na base de clientes.
6. Portaria MTP nº 3.717/2022 — prorrogações de prazo e eventuais alterações posteriores
   à 671/2021.

---

## 12. Referências

**Legislação e fontes oficiais**

- [Portaria MTP nº 671/2021 — texto integral](https://www.normaslegais.com.br/legislacao/portaria-mtp-671-2021.htm)
- [Perguntas e Respostas oficiais sobre REP — Ministério do Trabalho e Emprego](https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/inspecao-do-trabalho/fiscalizacao-do-trabalho/Perguntas%20e%20Respostas%20REP)
- [Perguntas e Respostas — Portaria nº 671/2021 (versão MTP)](https://www.gov.br/trabalho-e-previdencia/pt-br/composicao/orgaos-especificos/secretaria-de-trabalho/inspecao/fiscalizacao-do-trabalho/Perguntas%20e%20Respostas%20REP)

**Interpretação e leiautes**

- [Portaria 671/2021 — Espaço Legislação TOTVS](https://espacolegislacao.totvs.com/portaria-671/)
- [AFD conforme Portaria 671 — tipos de registro](https://suporte.topponto.com.br/duvida/afd-conforme-portaria-671/)
- [AEJ conforme Portaria 671 — tipos de registro](https://suporte.topponto.com.br/duvida/aej-conforme-portaria-671/)
- [Arquivos AFD, AFDT e ACJEF: o que mudou com a Portaria 671](https://www.pontotel.com.br/arquivos-afd-afdt-acjef/)
- [AEJ — Linha Protheus / TOTVS](https://centraldeatendimento.totvs.com/hc/pt-br/articles/9326209981719-RH-Linha-Protheus-PON-Arquivo-Eletr%C3%B4nico-de-Jornadas-AEJ-Portaria-671)
- [Espelho de ponto, AFD e AEJ: diferenças e riscos](https://certponto.com.br/espelho-de-ponto-afd-e-aej-diferencas-riscos-fechamento/)
- [Guia REP-C, REP-A e REP-P](https://useponto.com.br/blog/guia-pratico-portaria-671-2021)
- [Súmula 338 do TST e controle de ponto](https://www.mywork.com.br/blog/sumula-338-tst-controle-de-ponto)
- [Art. 58, §1º da CLT e Súmula 366 do TST](https://www.jusbrasil.com.br/jurisprudencia/busca?q=art.+58%2C+%C2%A7+1%C2%BA%2C+da+clt%2C+e+s%C3%BAmula+366%2Ftst)

**Odoo / OCA (branches 16.0 verificadas)**

- [Documentação Odoo 16 — Folha de Pagamento](https://www.odoo.com/documentation/16.0/pt_BR/applications/hr/payroll.html)
- [OCA/hr-attendance](https://github.com/OCA/hr-attendance/tree/16.0)
- [OCA/l10n-brazil — l10n_br_resource, l10n_br_fiscal_certificate](https://github.com/OCA/l10n-brazil/tree/16.0)
- [OCA/server-tools — auditlog](https://github.com/OCA/server-tools/tree/16.0)
- [OCA/queue — queue_job](https://github.com/OCA/queue/tree/16.0)
- [OCA/reporting-engine — report_qweb_signer, report_py3o, report_xlsx](https://github.com/OCA/reporting-engine/tree/16.0)
- [OCA/server-ux — base_tier_validation](https://github.com/OCA/server-ux/tree/16.0)

**Código analisado**

- `l10n_br_hr_payroll/models/hr_payslip.py`, `models/hr_contract.py`,
  `models/salary_rules_br.py`, `tests/test_worked_days.py`
- `l10n_br_hr_overtime_custom_multiplier/` (modelos, wizard, segurança)
- `docs/PRD-folha-pagamento-evolucao.md`
