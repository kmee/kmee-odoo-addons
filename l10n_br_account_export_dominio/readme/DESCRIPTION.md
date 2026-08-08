Exporta lançamentos contábeis no layout do **Domínio (Thomson Reuters)**.

**Formato:** TXT delimitado por pipe  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Cada linha começa **e termina** com o separador. Registros hierárquicos.

## Estrutura

### Registro `0000` (abertura do arquivo)

| Campo | Conteúdo | Formato |
|---|---|---|
| 1 | tipo de registro | `0000` |
| 2 | CNPJ da empresa | só dígitos |

### Registro `6000` (abertura do lançamento)

| Campo | Conteúdo | Formato |
|---|---|---|
| 1 | tipo | `6000` |
| 2 | indicador | `X` (lançamento com partidas) |
| 3-5 | reservados | vazios |

### Registro `6100` (partida)

| Campo | Conteúdo | Formato |
|---|---|---|
| 1 | tipo | `6100` |
| 2 | data | `dd/mm/aaaa` |
| 3 | conta de débito | código do escritório |
| 4 | conta de crédito | código do escritório |
| 5 | valor | vírgula decimal, sem milhar |
| 6 | código de histórico | vazio (não implementado) |
| 7 | histórico | texto, até 512 |
| 8-10 | reservados | vazios |

## Exemplo

```
|0000|12345678000195|
|6000|X||||
|6100|05/08/2026|1101|2201|1500,00||Venda de agosto||||
```

## Observações

- **Débito e crédito na mesma linha**: um lançamento simples gera um único `6100`.
- **Partidas múltiplas**: sem par único, cada linha detalha um lado e o outro recebe a conta `0`.
- Conferido campo a campo contra arquivo real gerado pelo próprio Domínio.

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
