Exporta lançamentos contábeis no layout do **SCI (Visual Sucessor / Único)**.

**Formato:** CSV separado por vírgula  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Uma linha por partida, com sequencial próprio e conta `0` no lado vazio.

## Estrutura

### Partida

| Campo | Conteúdo | Formato |
|---|---|---|
| 1 | sequencial | 6 dígitos com zeros à esquerda |
| 2 | data | `AAAAMMDD` |
| 3 | conta de débito | 8 dígitos, `0` quando credora |
| 4 | conta de crédito | 8 dígitos, `0` quando devedora |
| 5 | valor | **ponto** decimal |
| 6 | código de histórico | 8 dígitos |
| 7 | histórico | até 200 |
| 8 | documento | até 20 |
| 9 | CNPJ/CPF do parceiro | só dígitos |
| 10-11 | reservados | vazios |

## Exemplo

```
000001,20260805,00001101,0,1500.00,00000000,Venda de agosto,DOC123,,,
```

## Observações

- Este é o único layout da série que usa **ponto** como separador decimal.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
