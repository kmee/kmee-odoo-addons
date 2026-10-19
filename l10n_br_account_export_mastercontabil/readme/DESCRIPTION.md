Exporta lançamentos contábeis no layout do **Master Contábil**.

**Formato:** TXT posicional, 121 posições  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Data no início, valor com ponto decimal e sufixo fixo.

## Estrutura

### Partida

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-8 | data | `AAAAMMDD` |
| 9-16 | documento | 8 |
| 17-33 | conta de débito | 17 |
| 34-58 | conta de crédito | 25 |
| 59-66 | valor | 8, à direita, **ponto** decimal |
| 67-69 | reservado | espaços |
| 70-117 | histórico | 48 |
| 118-121 | sufixo | `0000` |

## Exemplo

```
20260805DOC123  1101             2201                      1500.00   Venda de agosto                       0000
```

## Observações

- O arquivo de referência usa a extensão `.D26` (ano da competência).

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
