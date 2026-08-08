Exporta lançamentos contábeis no layout do **IGNIS**.

**Formato:** CSV separado por ponto e vírgula, campos de largura fixa  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Híbrido: os campos são delimitados, mas cada um tem largura fixa própria.

## Estrutura

### Partida

| Campo | Conteúdo | Formato |
|---|---|---|
| 1 | data | `dd/mm/aaaa` |
| 2 | conta de débito | 20, alinhada à esquerda |
| 3 | conta de crédito | 20, alinhada à esquerda |
| 4 | valor | 19, alinhado à direita |
| 5 | documento | 10 |
| 6 | histórico | 66 |

## Exemplo

```
05/08/2026;1101                ;2201                ;            1500,00;DOC123    ;Venda de agosto...
```

## Observações

- Débito e crédito na mesma linha; partidas múltiplas usam o lado vazio.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
