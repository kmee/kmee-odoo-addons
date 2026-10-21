Exporta lançamentos contábeis no layout do **Oracle GL Interface**.

**Formato:** Planilha XLSX  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Colunas no vocabulário da interface do General Ledger.

## Estrutura

### Cabeçalho

| Campo | Conteúdo | Formato |
|---|---|---|
| A | ACCOUNTING_DATE |  |
| B | SEGMENT | código da conta |
| C | ENTERED_DR | valor a débito |
| D | ENTERED_CR | valor a crédito |
| E | REFERENCE | histórico |
| F | CURRENCY_CODE | moeda da empresa |

## Exemplo

```
ACCOUNTING_DATE | SEGMENT | ENTERED_DR | ENTERED_CR | REFERENCE | CURRENCY_CODE
```

## Observações

- Requer a biblioteca `xlsxwriter` no servidor.
- A aba da planilha se chama `GL_INTERFACE`.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
