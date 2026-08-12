Exporta lançamentos contábeis no layout do **Domínio com plano de contas**.

**Formato:** TXT delimitado por pipe, dois arquivos  
**Codificação:** Windows-1252 (ANSI), configurável  
**Valor:** sempre positivo (o lado é indicado por campo ou coluna)

Igual ao layout Domínio, mais um segundo arquivo com o plano de contas.

## Estrutura

### Registro `0200` (conta do plano)

| Campo | Conteúdo | Formato |
|---|---|---|
| 1 | tipo | `0200` |
| 2 | código da conta | código do escritório |
| 3 | classificação | `1` |
| 4 | tipo | `A` (analítica) |
| 5 | nome da conta | até 60 |
| 6 | data de criação | `dd/mm/aaaa` |
| 7 | natureza | `A` |

## Exemplo

```
|0200|1101|1|A|Receita de vendas|01/08/2026|A||||||
```

## Observações

- Enviar o plano junto tende a ser o que garante importação sem ajuste manual, porque as contas passam a existir no destino.
- Gera dois arquivos: os lançamentos e o plano (`..._plano_contas.txt`).

## O que o layout usa do Odoo

- **conta**: o campo *Código no escritório* (`l10n_br_export_code`) de cada conta, não o código do plano do Odoo;
- **histórico**: o rótulo da partida (`name`), ou a referência do lançamento quando vazio;
- **documento**: a referência do lançamento (`ref`);
- **data**: a data do lançamento (`date`).
