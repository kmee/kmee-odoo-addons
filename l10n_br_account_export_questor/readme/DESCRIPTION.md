Exporta lançamentos contábeis no layout do **Questor**.

**Formato:** TXT posicional, 445 posições  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Campos numéricos com zeros à esquerda e a data em dois formatos.

## Estrutura

### Partida

| Campo | Conteúdo | Formato |
|---|---|---|
| 1 | reservado | espaço |
| 2-6 | empresa | 5 dígitos |
| 7-26 | reservado | 20 dígitos |
| 27-34 | sequencial | 8 dígitos |
| 35-36 | tipo | `01` |
| 37-44 | data | `AAAAMMDD` |
| 45-54 | data | `dd/mm/aaaa` |
| 55-56 | origem | `LN` |
| 57-68 | documento | 12 |
| 69-80 | conta de débito | 12 dígitos |
| 81-92 | conta de crédito | 12 dígitos |
| 93-104 | valor | 12, centavos |
| 105-304 | histórico | 200 |

## Exemplo

```
 00001000000000000000000000000101202608050 5/08/2026LN DOC123     000000001101000000002201000000150000Venda de agosto
```

## Observações

- A data aparece duas vezes, em formatos diferentes.
- O Questor tem 13 layouts no mercado: este cobre o de lançamentos contábeis.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
