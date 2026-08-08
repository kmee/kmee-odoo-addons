Exporta lançamentos contábeis no layout do **Viasoft**.

**Formato:** TXT posicional  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Sequencial, data compacta, contas e valor em largura fixa.

## Estrutura

### Partida

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-3 | filial | `001` |
| 4-6 | sequencial | 3 dígitos |
| 7-14 | data | `ddmmaaaa` |
| 15-29 | conta de débito | 15 |
| 30-51 | conta de crédito | 22 |
| 52-61 | valor | 10, à direita |
| 62-64 | reservado | espaços |
| 65-164 | histórico | 100 |

## Exemplo

```
001001050820261101           2201                     1500,00   Venda de agosto
```

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
