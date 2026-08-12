Exporta lançamentos contábeis no layout do **Exactus**.

**Formato:** TXT posicional, 180 posições  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Campos numéricos zero-padded, data compacta no fim.

## Estrutura

### Partida

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-7 | sequencial | 7 dígitos |
| 8-22 | conta de débito | 15 dígitos |
| 23-37 | conta de crédito | 15 dígitos |
| 38-47 | documento | 10 |
| 48-147 | histórico | 100 |
| 148-162 | valor | 15, centavos |
| 163-168 | data | `ddmmaa` |

## Exemplo

```
0000001000000000001101000000000002201DOC123    Venda de agosto...000000000150000050826
```

## Observações

- Data no formato curto `ddmmaa`.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
