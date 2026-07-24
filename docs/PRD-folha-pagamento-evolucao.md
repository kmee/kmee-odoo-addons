# PRD — Evolução da Folha de Pagamento Brasileira (l10n_br_hr_*)

**Status:** rascunho para revisão · **Autor:** gerado a partir da revisão de código do PR #277 (branch `folha`) + parecer fiscal · **Data:** 2026-07-24
**Repositório:** kmee/kmee-odoo-addons · **Escopo:** conjunto de módulos de folha CLT/Estatutário, eSocial, benefícios, férias/13º, arquivos governamentais.

> Este documento NÃO é o escopo do PR #277 (que apenas corrige 2 bugs — ver §2). Ele consolida os achados da revisão de código dos 12 módulos de folha para orientar a evolução do produto. Valores fiscais citados vêm dos CSVs do próprio repo e da revisão; **conferência normativa final deve ser feita por especialista fiscal** (itens "verificar").

---

## 1. Contexto e problema

A folha de pagamento BR do repo cobre o ciclo CLT/Estatutário (proventos, INSS, IRRF, FGTS, adicionais), benefícios (VT/VR/VA/plano de saúde), férias/13º/rescisão, eSocial e arquivos governamentais (SEFIP/DIRF/CAGED). O núcleo mensal (INSS/IRRF competência 2024, holerite CLT) instala e é coberto por testes. Porém a revisão identificou:

- **Motor fiscal congelado em 2024** com fallback silencioso — cálculo incorreto em competências ≥ 2025 (produção 2026).
- **Duas fontes de verdade** para tabelas fiscais (constantes Python em `l10n_br_hr_payroll` vs. CSVs parametrizados por vigência em `l10n_br_esocial`), divergentes.
- Módulos periféricos (arquivos governamentais, horas extras customizadas) **não usáveis em produção** como estão.
- Funcionalidades prometidas nos READMEs (contribuição sindical, salário-substituição, descontos de ausências) **não implementadas** (cadastros sem efeito na folha).
- Testes que **consagram valores fiscalmente incorretos** (verdes confirmando erro).

## 2. Escopo do PR #277 (o que este PR entrega/corrige)

O PR #277 integra a folha e, nesta rodada de correção, resolve **apenas**:
- **Fix 1 (fiscal):** remoção do override incorreto da `BASE_IRRF` em `l10n_br_hr_benefit` — plano de saúde e VT não são dedutíveis na retenção mensal na fonte (art. 4º Lei 9.250/95; art. 677 RIR/2018; art. 52 IN RFB 1.500/2014). Restaura a fórmula base original.
- **Fix 2 (demo):** payslips demo deixam de depender do journal volátil (id=1) que o `l10n_generic_coa` recria — instalação com demo volta a funcionar.
- **Ajuste de teste:** `test_plano_saude_reduz_base_irrf` invertido/removido para refletir o comportamento fiscal correto.

Todo o restante deste PRD é **backlog de evolução** — NÃO faz parte do PR #277.

## 3. Objetivos e não-objetivos

**Objetivos**
1. Cálculo fiscal correto por competência (sem hardcode 2024) para INSS, IRRF, salário família, salário mínimo, dedução por dependente.
2. Férias, 13º e rescisão trabalhista e fiscalmente corretos.
3. eSocial funcional ponta-a-ponta (transmissão, retorno, recibo) para o ciclo mínimo.
4. Uma única fonte de verdade para tabelas fiscais, parametrizada por vigência.
5. Cobertura de testes que valide valores fiscais (não apenas presença de strings/registros).

**Não-objetivos (desta fase)**
- Reescrever os arquivos legados que devem migrar para eSocial (CAGED).
- Cobertura de todos os eventos eSocial da tabela (foco no ciclo mínimo DCTFWeb).

## 4. Requisitos priorizados

### P0 — risco fiscal/funcional imediato (bloqueiam uso em produção)

**Motor fiscal (l10n_br_hr_payroll)**
- **RF-01 — Tabelas por competência:** eliminar `INSS_TABELAS`/`IRRF_TABELAS`/`SALARIO_MINIMO`/`SALARIO_FAMILIA_*` hardcoded (`models/salary_rules_br.py:34-71`); resolver faixas pela data da folha a partir de modelo parametrizado por vigência (promover os CSVs de `l10n_br_esocial/data/l10n_br.esocial.faixa.*`, convertendo `Char`→`Float`). **Falhar com `UserError` se não houver tabela vigente** — nunca cair silenciosamente em 2024 (`:84,109,120`). As regras de férias/13º/rescisão devem **passar o ano** para `calc_inss/calc_irrf` (`l10n_br_hr_vacation/data/*_data.xml`).
- **RF-02 — Salário família:** corrigir tabela extinta de 2 faixas (`salary_rules_br.py:62-65`) para faixa única vigente; corrigir base (remuneração vs. `contract.wage`, `hr_salary_rule_data.xml:141`); corrigir testes que fixam o valor errado.
- **RF-03 — Pensão alimentícia:** hoje reduz a base do IRRF mas **nunca é descontada do líquido**. Criar rubrica DED de desconto + suportar % sobre remuneração (não só valor fixo) (`hr_employee.py:24`; base + férias/13º).

**Férias / 13º / rescisão (l10n_br_hr_vacation)**
- **RF-04 — Abono pecuniário:** hoje paga 40 dias (30 férias + 10 abono; `data/hr_salary_rule_ferias_data.xml:22,58`). Corrigir para férias proporcionais aos dias gozados; adicionar **1/3 constitucional sobre o abono**; e **não tributar** o abono (verba indenizatória — sem INSS por Lei 8.212 art. 28 §9º, sem IRRF por ADI SRF 5/2005; hoje está na categoria ALW `:49`).
- **RF-05 — 2ª parcela do 13º:** a linha `NET` não deduz a 1ª parcela (`13_data.xml:141-153`) — risco de **pagamento em dobro** para quem baseia pagamento/contabilização na linha. Transformar a dedução do adiantamento em regra DED na estrutura.
- **RF-06 — Rescisão:** `structure_rescisao` (`hr_payroll_structure_data.xml:70-82`) não tem INSS/IRRF/FGTS/saldo de salário/férias vencidas+1/3/aviso prévio — **inutilizável em produção**. Implementar verbas rescisórias ou marcar explicitamente como placeholder e desabilitar.

**Arquivos governamentais (l10n_br_hr_arquivos_governo) — não usável**
- **RF-07 — Código de verba errado:** SEFIP (`models/l10n_br_hr_sefip.py:217`) e DIRF (`models/l10n_br_hr_dirf.py:203`) buscam a linha `"BRUTO"`, que não existe (o código é `GROSS`, `l10n_br_hr_payroll/data/hr_salary_rule_data.xml:192`) → remuneração/RTRT saem **R$ 0,00 sempre**.
- **RF-08 — DIRF inválida:** RTRT/RTPO devem ser 1 registro com 13 campos mensais (jan–dez+13º); o código gera 12 registros e omite o 13º (`dirf.py:200-215`). IRRF gravado como `RTDP` (dedução de dependentes) em vez de `RTIRF` (`:213-215`). CNPJ truncado usado como CPF do responsável (`:153-159`). Retificadora/recibo nunca entram no arquivo (`:149`).
- **RF-09 — SEFIP fora do leiaute:** registros não posicionais de 360 bytes; campos de configuração (código recolhimento, FPAS, CNPJ) nunca entram; `zfill` invertido em campos numéricos (`sefip.py:188,222`); CNPJ calculado e descartado (`:170`); mês 13 sem filtro de data (`:143-157`).
- **RF-10 — CAGED extinto:** substituído por eSocial (S-2200/S-2299) desde 2020 (`l10n_br_hr_caged.py`). No mínimo avisar; idealmente remover/redirecionar para eSocial.

**Horas extras (l10n_br_hr_overtime_custom_multiplier)**
- **RF-11 — Crash:** `models/hr_attendance_overtime.py:73,75` usa `overtime_range.total` (campo inexistente; é `total_hours`) → `AttributeError` em múltiplas faixas.
- **RF-12 — Locale:** `hr_overtime_multiplier_range.py:42` usa `strftime("%A").lower()` (depende de locale) → com pt_BR o domain fica vazio e `search([])` retorna **todas as faixas** (multiplicador errado). Usar `weekday()`.
- **RF-13 — Segurança:** ACLs dão CRUD (incl. unlink) a `base.group_user` (`security/hr_attendance_exception.xml`, `hr_overtime_multiplier_range.xml`) — qualquer usuário edita faixas de pagamento de HE. Restringir escrita a `hr_attendance.group_hr_attendance_manager`.

**eSocial (l10n_br_esocial)**
- **RF-14 — id_evento nunca casado:** `id_evento` não é atribuído em lugar nenhum → o matching do retorno (`models/esocial_lote.py:217-223`) nunca casa; eventos ficam presos em `sent` sem recibo/ocorrência. Extrair o Id do XML gerado e persistir.

### P1 — robustez e completude
- **RF-15** — `_get_baselocaldict` extensível: derivar os codes pré-populados das regras da estrutura em vez da tupla fixa (`l10n_br_hr_payroll/models/hr_payslip.py:79-85`) — previne a classe de bug do IRRF em todos os satélites.
- **RF-16** — IRRF desconto simplificado mensal (vigente desde 05/2023): aplicar o mais favorável (`hr_salary_rule_data.xml:262-293`).
- **RF-17** — `l10n_br_hr_payroll_account`: entregar mapeamento regra→conta (data/demo) + `default_account_id`/`company_id` no diário FOPAG (`data/account_journal_data.xml`) — hoje o wiring só existe no teste.
- **RF-18** — Médias de HE/adicionais em férias e 13º (Súmula 45 TST / CLT art. 142); hoje usam `contract.wage` seco.
- **RF-19** — Férias respeitarem dias de direito (24/18/12 por faltas) e permitir fracionamento (reforma trabalhista); campo `l10n_br_dias_ferias_gozadas` hoje é morto.
- **RF-20** — `l10n_br_hr_holiday`: ligar os campos declarativos (`l10n_br_payroll_discount`, `l10n_br_discount_dsr`, `l10n_br_need_attachment`, `l10n_br_days_limit`) à folha e às validações do `hr.leave` (avaliar reuso de `hr_holidays_required_support_document`).
- **RF-21** — `l10n_br_hr_syndicate`: implementar a contribuição sindical em folha (rubrica) e o piso salarial prometidos no README — hoje é cadastro sem efeito.
- **RF-22** — `l10n_br_hr_substituicao`: gerar a diferença de salário-substituição (CLT art. 450 / Súmula 159 TST) no holerite do substituto; constraint de sobreposição.
- **RF-23** — `l10n_br_hr_gerador_holerite`: impedir duplicidade de competência/contrato (`models/hr_payslip_generator.py:64-86`).
- **RF-24** — `l10n_br_hr_validacao_folha`: duplicidade por **sobreposição de período** (não datas exatas); validar dígitos de CPF (usar `erpbrasil.base.fiscal`).
- **RF-25** — eSocial: homogeneidade do lote (bloquear grupos mistos); S-1200 (filtrar `total==0`, validar matrícula, suportar `ind_retif`/`nrRecibo`); eventos do ciclo mínimo (S-1005, S-1210, S-1299/S-1298, S-3000, totalizadores S-5001/S-5002/S-5003).

### P2 — qualidade / higiene
- **RF-26** — Divisor de jornada do contrato em vez de `220` fixo (`hr_salary_rule_data.xml:53,70,87`); DSR por dias úteis reais em vez de `4/26` (`:178-179`).
- **RF-27** — Mover `l10n_br_tipo_contrato` de `hr.employee` para `hr.contract` (com migração).
- **RF-28** — Copyright/licença headers em `l10n_br_esocial`, `arquivos_governo`, `gerador_holerite`, `overtime`; `_()` em notificações; remover fallback de API privada da esociallib (`base_intermediario.py:90-100`).
- **RF-29** — Guardas de estado/auditoria em `action_mark_success/error` do eSocial (`esocial_evento.py:114-120`) e nas actions de `substituicao`/`overtime`.
- **RF-30** — Remover código morto comentado (`overtime/models/hr_attendance.py:30-110`); não sequestrar o menuitem core (`overtime/views/hr_attendance_overtime.xml:114-118`); `weekday()`/`digits`/`_description` no wizard de overtime.

## 5. Riscos fiscais destacados (para validação por especialista)
1. Competência ≥ 2025 com tabela 2024 (INSS/IRRF/teto/isenção) — sub/super-retenção sistemática. **Maior risco.**
2. Novo regime de isenção do IRRF a partir de 01/2026 (até ~R$ 5.000) — sem tratamento no motor nem nos CSVs.
3. Salário família em faixa/valor extintos — pagamento indevido + divergência com eSocial/DCTFWeb.
4. Abono de férias tributado (INSS/IRRF) sendo indenizatório.
5. Pensão alimentícia deduzida do IRRF sem ser retida — inconsistência com S-1200/DIRF.
6. CONTRIB_RPPS genérica (alíquota varia por ente federativo pós-EC 103) — definir público-alvo.
7. 13º/rescisão: avos no mês de desligamento (regra dos 15 dias só no mês de admissão), sem verbas rescisórias.
8. S-1200 usa `abs(total)` — sinal depende 100% da classificação `tp_rubr`; rubrica mal classificada inverte provento/desconto sem erro.

## 6. Estratégia de testes (lacunas prioritárias)
- **Competência ≠ 2024**: payslip 2025/2026 (exporia o fallback silencioso) — teste mais barato e mais importante ausente.
- Valores fiscais exatos (não só presença): INSS/IRRF de férias e 13º; SEFIP/DIRF com asserção de valor e largura posicional (exporia o bug `BRUTO`→zerado).
- Pensão descontada do líquido; abono com 1/3 e isenção; 2ª parcela 13º na linha NET; rescisão com desligamento antes do dia 15.
- eSocial: `action_transmitir/consultar` com mock da `esociallib` (assinatura, grupo, matching de retorno, `id_evento`).
- `l10n_br_hr_overtime_custom_multiplier`: **zero testes** — criar (faixa única, múltiplas faixas, feriado, locale, wizard).
- Corrigir testes que consagram bug: salário família (valor antigo), abono de férias (40 dias).
- Convenções: `@tagged("post_install","-at_install")` + `tracking_disable` nos commons de teste.

## 7. Fora de escopo / decisões pendentes
- Definir se `syndicate`/`substituicao` ganham as regras que os READMEs prometem ou se os READMEs são ajustados.
- Definir público-alvo do RPPS (federal progressivo vs. municipal flat).
- 2ª rodada de revisão de código dedicada aos módulos secundários (esta rodada priorizou payroll/payroll_account/esocial em profundidade).

## 8. Referências
- Parecer fiscal (base da §2 Fix 1): art. 4º Lei 9.250/95; art. 677 Decreto 9.580/2018 (RIR/2018); arts. 52-54 IN RFB 1.500/2014.
- Revisão de código: 3 relatórios (módulos prioritários + grupos A/B) — 12 módulos, achados com arquivo:linha.
