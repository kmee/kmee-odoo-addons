Exporta lançamentos contábeis no layout do **Systempro**.

**Formato:** TXT posicional, 544 posições  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Uma linha por partida, competência no início.

## Estrutura

### Partida

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-6 | competência | `AAAAMM` |
| 7-8 | dia | `dd` |
| 9-12 | reservado | 4 dígitos |
| 13-17 | conta | 5, à direita |
| 18-217 | histórico | 200 |

## Exemplo

```
20260805000  1101Venda de agosto
```

## Observações

- O layout de referência não traz o valor na linha de movimento: confirme com o escritório antes do primeiro envio.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
