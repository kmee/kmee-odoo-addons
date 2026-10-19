Exporta lançamentos contábeis no layout do **Alterdata (WCont)**.

**Formato:** CSV, campos entre aspas duplas, separados por vírgula  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Uma linha por partida: o lado sem valor fica com a conta vazia.

## Estrutura

### Partida

| Campo | Conteúdo | Formato |
|---|---|---|
| 1 | reservado | vazio |
| 2 | conta de débito | preenchida só se a partida é devedora |
| 3 | conta de crédito | preenchida só se a partida é credora |
| 4 | data | `dd/mm/aaaa` |
| 5 | valor | vírgula decimal |
| 6 | reservado | vazio |
| 7 | histórico | até 200 |
| 8 | documento | até 30 |

## Exemplo

```
"","1101","","05/08/2026","1500,00","","Venda de agosto","DOC123"
"","","2201","05/08/2026","1500,00","","Venda de agosto","DOC123"
```

## Observações

- O importador do WCont é configurável: confirme a ordem das colunas com o escritório.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
