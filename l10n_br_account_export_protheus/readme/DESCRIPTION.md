Exporta lançamentos contábeis no layout do **TOTVS Protheus**.

**Formato:** TXT posicional, 139 posições  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Largura fixa, valor em centavos sem separador.

## Estrutura

### Partida

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-6 | sequencial | zeros à esquerda |
| 7-9 | reservado | espaços |
| 10-49 | conta de débito | 40, à esquerda |
| 50-79 | conta de crédito | 30, à esquerda |
| 80-96 | valor | 17, **centavos** com zeros à esquerda |
| 97-99 | reservado | espaços |
| 100-139 | histórico | 40 |

## Exemplo

```
000001   1101                                    2201                          00000000000150000   Venda de agosto
```

## Observações

- Valor em centavos: R$ 1.500,00 vira `00000000000150000`.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
