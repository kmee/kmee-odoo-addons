Exporta lançamentos contábeis no layout do **Prosoft**.

**Formato:** TXT com registros `LC1` e `LC2`  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Um cabeçalho por lançamento (`LC1`) e um detalhe por partida (`LC2`).

## Estrutura

### Registro `LC1` (cabeçalho do lançamento)

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-3 | tipo | `LC1` |
| 4-8 | sequencial | 5 dígitos |
| 9-11 | reservado | espaços |
| 12-19 | data | `ddmmaaaa` |
| 20-29 | documento | 10 |
| 30-34 | reservado | espaços |
| 35-64 | origem | `Omie` |

### Registro `LC2` (partida)

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-3 | tipo | `LC2` |
| 4-8 | sequencial do lançamento | 5 dígitos |
| 9-11 | sequência da partida | 3 dígitos |
| 12 | natureza | `D` ou `C` |
| 13-32 | conta | 20 |
| 33-52 | valor | 20, à direita, ponto decimal |
| 53-152 | histórico | 100 |

## Exemplo

```
LC100001   05082026DOC123         Omie
LC200001001D1101                             1500.00Venda de agosto
```

## Observações

- A natureza da partida vai no campo `D`/`C`, e não por coluna.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
