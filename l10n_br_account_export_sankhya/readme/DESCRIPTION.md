Exporta lançamentos contábeis no layout do **Sankhya**.

**Formato:** Planilha XLSX  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Uma linha por partida, com cabeçalho de colunas.

## Estrutura

### Cabeçalho

| Campo | Conteúdo | Formato |
|---|---|---|
| A | Data |  |
| B | Conta | código do escritório |
| C | Debito | numérico |
| D | Credito | numérico |
| E | Historico |  |
| F | Documento |  |

## Exemplo

```
Data | Conta | Debito | Credito | Historico | Documento
```

## Observações

- Requer a biblioteca `xlsxwriter` no servidor.
- Valores gravados como número, com formato de moeda na planilha.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
