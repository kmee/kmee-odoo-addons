Consulta: Compras > Relatórios > Compras comprometidas a pagar (lista, tabela
dinâmica por mês de vencimento e gráfico).

No MIS Builder, para somar as compras comprometidas ao fluxo de caixa previsto:

#. Em um relatório MIS de fluxo de caixa, crie um KPI "Compras comprometidas"
   com a expressão de saldo da conta a pagar (por exemplo ``-balp[2101%]``,
   conforme o plano de contas) e, na instância do relatório, uma coluna cuja
   fonte seja "Compras comprometidas a pagar"
   (``mis.purchase.commitment.due``).
#. Ou use a tabela como "Move lines source" de um relatório próprio de
   compromissos a pagar.
