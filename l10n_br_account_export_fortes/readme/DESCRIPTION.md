Exporta lançamentos contábeis no layout do **Fortes AG**.

**Formato:** TXT com registros identificados, extensão `.CT`  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Registro de abertura seguido de um registro por partida.

## Estrutura

### Registro `0010` (abertura)

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-4 | tipo | `0010` |
| 5-14 | origem | `AC` |
| 15-24 | sistema | `OMIE` |
| 25-28 | código da empresa | da configuração |
| 29-36 | data inicial | `AAAAMMDD` |
| 37-44 | data final | `AAAAMMDD` |
| 45-84 | descrição | 40 |

### Registro `1004` (partida)

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-4 | tipo | `1004` |
| 5-12 | data | `AAAAMMDD` |
| 13-22 | sequencial | 10 dígitos |
| 23-28 | competência | `AAAAMM` |
| 29-32 | reservado | espaços |
| 33-52 | conta | 20 |
| 53-72 | valor | 20, à direita, ponto decimal e **6 casas** |
| 73-112 | histórico | 40 |

## Exemplo

```
0010AC        OMIE      1   2026080120260831Integracao contabil
10042026080500000000012026081101                          1500.000000Venda de agosto
```

## Observações

- Seis casas decimais no valor, particularidade do layout.
- O código da empresa vem do campo **Código da empresa no escritório** da configuração.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
