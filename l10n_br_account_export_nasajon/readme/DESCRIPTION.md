Exporta lançamentos contábeis no layout do **Nasajon**.

**Formato:** TXT posicional  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Uma linha por partida, data curta no início.

## Estrutura

### Partida

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-4 | data | `ddmm` |
| 5 | reservado | 1 dígito |
| 6-25 | conta | 20 |
| 26-30 | reservado | espaços |
| 31-80 | histórico | 50 |
| 81-96 | valor | 16, à direita |
| 97 | separador | espaço |
| 98-117 | documento | 20 |

## Exemplo

```
050801101                    Venda de agosto                            1500,00 DOC123
```

## Observações

- O Nasajon aceita várias variantes de arquivo; esta cobre o movimento contábil.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
