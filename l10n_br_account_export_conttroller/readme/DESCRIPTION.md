Exporta lançamentos contábeis no layout do **Conttroller**.

**Formato:** CSV separado por ponto e vírgula  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Uma linha por partida, com débito e crédito em **colunas separadas**.

## Estrutura

### Partida

| Campo | Conteúdo | Formato |
|---|---|---|
| 1 | período | `AAAAMM` |
| 2 | sequencial |  |
| 3 | conta | código do escritório |
| 4 | centro de custo | `000` |
| 5 | reservado | 6 dígitos |
| 6 | data | `dd/mm/aaaa` |
| 7 | histórico | até 200 |
| 8 | valor a débito | preenchido só se devedora |
| 9 | valor a crédito | preenchido só se credora |
| 10 | reservado | vazio |

## Exemplo

```
202608;1;1101;000;000000;05/08/2026;Venda de agosto;1500,00;;
202608;2;2201;000;000000;05/08/2026;Venda de agosto;;1500,00;
```

## Observações

- O valor aparece na coluna do lado correspondente, e a outra fica vazia.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
