A ponte entre o registro de ponto e a folha de pagamento.

Antes deste módulo, `l10n_br_hr_payroll` recebia horas extras, horas noturnas
e faltas **digitadas à mão** no holerite, e os dias trabalhados vinham do
calendário do contrato, não da presença efetiva. A folha ficava descolada da
realidade fática da jornada, que é exatamente o que a fiscalização e a Justiça
do Trabalho cobram.

O que passa a ser derivado da apuração:

| Campo do holerite | Origem |
| --- | --- |
| `l10n_br_horas_extras_50` | Soma das horas extras apuradas na faixa de 50% |
| `l10n_br_horas_extras_100` | Soma das horas extras apuradas na faixa de 100% |
| `l10n_br_horas_noturnas` | Interseção com a janela das 22h às 5h |
| `l10n_br_faltas_injustificadas` | Faltas sem ocorrência que abone |
| `worked_days_line_ids` | Dias de presença efetiva, faltas e ausências abonadas |

Os campos continuam editáveis: quando não há apuração no período, o
comportamento antigo é preservado, e quem ainda digita continua digitando.

Rubricas novas:

- **DSR sobre horas extras** (Lei 605/49; Súmula 172 do TST), calculado sobre
  o valor das horas extras com os dias úteis e de repouso do período apurado;
- **Intervalo intrajornada suprimido** (art. 71, § 4º da CLT), pago com 50% e
  de natureza **indenizatória** - por isso vai para a categoria `IND`, que
  entra no líquido mas fica fora do bruto e das bases de INSS e IRRF.

Por fim, holerite que diverge de uma apuração **fechada** não é validado sem
justificativa registrada: fechar a competência e depois digitar outro número
sem dizer por quê é o caminho mais curto para perder uma reclamatória.
