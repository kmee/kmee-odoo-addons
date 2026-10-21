Exporta lançamentos contábeis no layout do **Calima ERP Contábil**.

**Formato:** TXT com registros de larguras diferentes  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Registro de abertura (252 posições) e um registro `301` por partida (597).

## Estrutura

### Registro `abertura` (identificação)

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-8 | sequência | `00000002` |
| 9-18 | data de geração | `dd/mm/aaaa` |
| 19-32 | CNPJ | só dígitos |
| 33-42 | data inicial | `dd/mm/aaaa` |
| 43-52 | data final | `dd/mm/aaaa` |
| 53-152 | descrição | 100 |

### Registro `301` (partida)

| Campo | Conteúdo | Formato |
|---|---|---|
| 1-3 | tipo | `301` |
| 4-13 | data | `dd/mm/aaaa` |
| 14 | origem | `R` |
| 15-32 | conta de débito | 18 |
| 33-50 | conta de crédito | 18 |
| 51-59 | valor | 9, centavos |
| 60-259 | histórico | 200 |

## Exemplo

```
0000000208/08/20261234567800019501/08/202631/08/2026Arquivo de integracao...
30105/08/2026R1101              2201              000150000Venda de agosto
```

## Observações

- As duas larguras (252 e 597) são verificadas por teste.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
