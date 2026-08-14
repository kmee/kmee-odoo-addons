# Estado da implementação: Controle de Ponto Brasileiro (Portaria MTP 671/2021)

**Data:** 2026-08-14 · **Branch:** `16.0-hr-attendance-ponto` ·
**PRD:** `PRD-controle-ponto-brasileiro.md`

Documento de estado da frente de ponto. O PRD descreve o alvo; aqui está o que
já existe em código, como foi validado e o que ficou de fora.

## 1. O que foi entregue

Cinco módulos novos, cobrindo as fases 1 a 4 do PRD (todo o P0 de código):

| Módulo | Requisitos | Papel |
| --- | --- | --- |
| `l10n_br_hr_attendance` | RP-01 a RP-04 | Cadastro de REP, NSR, marcação imutável, conciliação por CPF/PIS, flags de contrato |
| `l10n_br_hr_attendance_afd` | RP-05 a RP-08 | Leitura e geração do AFD (Anexo V e leiaute 1.510), CRC-16, lacunas de NSR, importação idempotente |
| `l10n_br_hr_attendance_apuracao` | RP-09 a RP-15 | Motor de jornada: tolerância, intervalos, noturno, horas extras, faltas, fechamento |
| `l10n_br_hr_payroll_attendance` | RP-16 a RP-19 | Ponte com a folha: fim da digitação manual, `worked_days` da presença efetiva, rubricas novas |
| `l10n_br_hr_attendance_aej` | RP-20 a RP-23 | AEJ (Anexo VI), espelho de ponto, assinatura CAdES, retenção dos arquivos |

### Decisões de arquitetura tomadas na implementação

1. **Marcação e sessão são modelos distintos.** O AFD entrega marcações
   individuais; o `hr.attendance` do Odoo é um par entrada/saída. Criamos
   `l10n_br.hr.marcacao` como registro de origem imutável e passamos a derivar
   o `hr.attendance` dele na apuração. Isso resolve de uma vez o risco R7 do
   PRD (múltiplos pares por dia por causa da intrajornada), preserva a
   compatibilidade com o módulo de multiplicador de horas extras que já existe
   e dá lugar natural ao NSR e ao hash.

2. **Imutabilidade por `write`/`unlink` bloqueados, não por convenção.** Os
   campos que descrevem o fato registrado recusam alteração; pareamento,
   conciliação e desconsideração com motivo continuam livres, porque são atos
   de tratamento autorizados pelo art. 82. A permissão de gravar os campos
   protegidos existe só dentro do helper de criação e morre no retorno.

3. **Leiaute em módulo puro, sem ORM.** `afd_layout.py`, `afd_parser.py`,
   `afd_crc.py`, `aej_layout.py` e `regras_jornada.py` não importam Odoo. Dá
   para testar o CRC contra o vetor da própria Portaria e as regras da CLT
   contra o texto legal sem subir banco.

4. **Sem dependência dos módulos OCA de `hr-attendance`.** O PRD sugeria
   reusar `hr_attendance_reason`, `_modification_tracking` e afins. Nenhum
   deles é aderente à Portaria (não têm NSR, AFD, AEJ nem imutabilidade), e
   cada dependência nova obriga o cliente a agregar mais um repositório. A
   base é o `hr_attendance` do core; compor com os módulos OCA continua
   possível e está documentado nos READMEs.

5. **Verba indenizatória tem categoria própria (`IND`).** O intervalo
   suprimido do art. 71, § 4º entra no líquido mas fica fora do bruto, que é a
   base de INSS e IRRF. Como os dados do `l10n_br_hr_payroll` são
   `noupdate="1"`, o vínculo das rubricas novas à estrutura CLT e o ajuste da
   regra de líquido vão por `post_init_hook` idempotente.

### Fonte dos leiautes

Anexos V (AFD), VI (AEJ), VII (Atestado Técnico) e IX (requisitos do REP-P) da
Portaria MTP nº 671/2021, conferidos campo a campo contra duas transcrições
independentes do texto oficial. O CRC-16/KERMIT foi validado contra o vetor de
conferência da própria Portaria (`123456789` produz `0x2189`).

## 2. Validação

Rodada em banco descartável no `erplivre-odoo-16`:

```
0 failed, 0 error(s) of 344 tests
```

São 141 testes novos e os 203 já existentes do `l10n_br_hr_payroll`, que
continuam passando com a ponte instalada - o que confirma o RP-17: sem
apuração no período, a folha mantém o comportamento antigo.

Cobertura dos testes novos, por área:

- **CRC-16**: vetor oficial, bytes x texto, hexadecimal minúsculo, adulteração;
- **AFD**: tamanho de cada tipo de registro do Anexo V, ida e volta, fuso,
  leiaute 1.510 com fuso parametrizado, CRC divergente, lacuna de NSR, trailer
  inconsistente, data inválida, registro tipo 7 com hash, nome do arquivo;
- **Importação**: análise sem gravar, idempotência, arquivo estendido,
  pendência de conciliação, reconciliação posterior, contador de NSR;
- **Imutabilidade**: `write` e `unlink` recusados, tratamento permitido,
  motivo obrigatório, NSR único por REP, troca de vínculo recusada;
- **Regras da CLT**: tolerância (inclusive a regra "tudo ou nada" da Súmula
  366), pareamento com marcação ímpar, adicional noturno cruzando a
  meia-noite, hora reduzida, intrajornada com piso negociado, período
  suprimido, interjornada, DSR sobre horas extras, desconto de DSR por semana;
- **Apuração**: jornada padrão, extras, atraso, domingo, feriado, marcação
  desconsiderada, contrato dispensado, fechamento e seus bloqueios;
- **Folha**: quatro campos derivados, `worked_days` da presença efetiva,
  ausência abonada, rubricas novas, verba indenizatória fora do bruto,
  divergência bloqueando validação;
- **AEJ**: estrutura, contagem de campos por registro, cabeçalho, REPs,
  vínculos, `durJornada` em minutos, pareamento, horário contratual na
  primeira entrada, fuso obrigatório, desconsideração com motivo, faltas, DSR,
  banco de horas, PTRP, trailer, geração do anexo, ausência de certificado,
  espelho de ponto renderizado, ISO-8859-1.

`pre-commit` do repositório: verde (black, flake8, pylint_odoo, prettier-xml,
geração de README e de `setup.py`).

## 3. O que ficou fora, e por quê

**P1 - REP-P (fase 5 do PRD, RP-25 a RP-29).** A infraestrutura já está
pronta: o registro tipo 7 do AFD é gerado, o hash SHA-256 encadeado está
implementado e testado, e o cadastro de REP aceita o número do INPI. Falta a
camada de captura (portal/quiosque), o comprovante em PDF assinado (PAdES) e a
janela de 48 horas. O **registro do programa no INPI** e o **Atestado Técnico**
(RP-24, RP-29) são entregáveis regulatórios, não de código, e dependem de
decisão da KMEE sobre quem assina - é o risco R1 do PRD.

**P1 - banco de horas (RP-30).** O campo de saldo diário existe e já é
exportado no registro 07 do AEJ; falta a política de compensação, o prazo de
6/12 meses do art. 59 e o expurgo no vencimento.

**P1 - escala 12x36 (RP-32) e drivers de coleta por fabricante (RP-34).** O
motor lê a jornada do `resource.calendar`, então o 12x36 depende de calendário
de duas semanas e de regra própria de DSR e feriado. Os drivers são transporte
de arquivo (pasta, FTP, HTTP); o núcleo já trata o conteúdo.

**P2 - LGPD, perfis e painéis (RP-36 a RP-41).** O grupo de auditor somente
leitura e as regras de registro por funcionário já existem. Falta a política
de retenção e descarte, o log de acesso, a detecção de ponto britânico e o
painel de conformidade.

## 4. Pendências que dependem de decisão

1. **Dados do PTRP no registro 08 do AEJ.** Os parâmetros
   `l10n_br_hr_attendance_aej.ptrp_*` estão em branco de propósito: quem
   preenche é o desenvolvedor que assina o Atestado Técnico do art. 89.
2. **Responsável legal e técnico do Atestado.** Caminho crítico da fase 4 do
   PRD; sem ele o cliente não pode usar o sistema (art. 89, § 4º).
3. **Validador oficial de AEJ.** Não foi localizado validador público para o
   critério de aceite nº 2 do PRD. Os testes conferem o leiaute contra o texto
   do Anexo VI, o que é necessário mas não substitui um validador.
4. **Amostras reais de AFD** dos fabricantes da base instalada (RP-41). Os
   testes usam arquivos gerados pelo próprio leiaute; amostra real de
   fabricante é complemento que ainda falta.
