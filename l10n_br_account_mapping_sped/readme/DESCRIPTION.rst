Liga os planos de contas de destino ao **plano referencial da RFB**, que é a
base do registro **I051** do SPED Contábil (ECD): o mapeamento entre cada conta
da empresa e a conta correspondente do plano referencial.

Como funciona:

1. Crie um plano de destino marcado como **Plano referencial da RFB**, com o
   código do plano na tabela oficial (campo ``COD_PLAN_REF`` do I051; por
   exemplo, PJ em geral do Lucro Real usa o plano 1).
2. Vincule as contas do Odoo às contas referenciais, como em qualquer plano de
   destino (N contas do Odoo por conta referencial).
3. Aponte o plano na empresa (campo *Plano referencial da RFB*).

O gerador da ECD consome ``account.l10n_br_sped_referential_line()``: para cada
conta do I050, o método devolve ``COD_PLAN_REF``/``COD_CTA_REF`` quando a conta
está mapeada, ou vazio quando não está (o I051 é opcional por conta).

**Carga da tabela oficial**: as contas do plano referencial são publicadas pela
RFB nas tabelas dinâmicas do SPED (site do SPED, ECF/ECD). Importe-as pelo
import padrão do Odoo no modelo *Conta do Plano de Destino* (colunas: plano,
código, nome). Os dados de demonstração deste módulo são apenas ilustrativos.
