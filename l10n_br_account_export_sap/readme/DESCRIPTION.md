Exporta lançamentos contábeis no layout do **SAP**.

**Formato:** Planilha XLSX  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Uma linha por partida, com moeda explícita.

## Estrutura

### Cabeçalho

| Campo | Conteúdo | Formato |
|---|---|---|
| A | Data lancamento |  |
| B | Conta | código do escritório |
| C | Debito | numérico |
| D | Credito | numérico |
| E | Texto | histórico |
| F | Documento |  |
| G | Moeda |  |

## Exemplo

```
Data lancamento | Conta | Debito | Credito | Texto | Documento | Moeda
```

## Observações

- Requer a biblioteca `xlsxwriter` no servidor.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
