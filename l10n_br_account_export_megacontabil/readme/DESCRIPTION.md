Exporta lançamentos contábeis no layout do **Mega Contábil**.

**Formato:** TXT com registros identificados por prefixo  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Cabeçalho de identificação seguido das partidas.

## Estrutura

### Registro `00` (identificação do sistema)

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-2 | tipo | `00` |
| 3+ | nome | `MEGACONTABIL` |

### Registro `01` (empresa)

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-2 | tipo | `01` |
| 3+ | CNPJ | formatado |

### Registro `02` (partida)

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-2 | tipo | `02` |
| 3-10 | data | `ddmmaaaa` |
| 11-25 | conta de débito | 15 |
| 26-40 | conta de crédito | 15 |
| 41-55 | valor | 15, à direita |
| 56-155 | histórico | 100 |

## Exemplo

```
00MEGACONTABIL
0112.345.678/0001-95
02050820261101           2201                   1500,00Venda de agosto
```

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
