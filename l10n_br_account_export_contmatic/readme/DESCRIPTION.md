Exporta lançamentos contábeis no layout do **Contmatic Phoenix**.

**Formato:** TXT posicional, 332 posições  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Prefixo fixo `68`, data sem ano e valor com três decimais.

## Estrutura

### Partida

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-2 | prefixo | `68` |
| 3-7 | sequencial | 5 dígitos |
| 8-12 | data | `dd/mm` (sem ano) |
| 13-19 | conta de débito | 7 |
| 20-38 | conta de crédito | 19 |
| 39-50 | valor | 12, à direita, **ponto** decimal e 3 casas |
| 51-54 | reservado | espaços |
| 55-254 | histórico | 200 |

## Exemplo

```
680000105/081101   2201                    1500.000    Venda de agosto
```

## Observações

- O ano não vai na linha: vem do período da exportação.
- Três casas decimais, diferente do restante da série.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
