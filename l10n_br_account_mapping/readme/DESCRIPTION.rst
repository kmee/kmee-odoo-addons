Mapeia as contas do plano do Odoo para **planos de contas externos**: o plano do
escritório de contabilidade que recebe a exportação contábil e o plano
referencial da RFB usado no registro I051 do SPED Contábil.

Uma empresa pode ter vários planos de destino ao mesmo tempo (dois escritórios,
período de transição, referencial). Em cada plano, o registro central é a
**conta do destino** (código e nome como o destino a conhece), e um vínculo diz
quais contas do Odoo desaguam nela: **N contas do Odoo para 1 conta do
destino**, que é a relação típica com o plano mais enxuto do escritório.

Uma conta do Odoo só pode desaguar em uma conta por plano (o código exportado
seria ambíguo); em planos diferentes, cada conta pode cair onde precisar.

O desenho espelha o ``account_consolidation`` do Odoo Enterprise
(``consolidation.chart``/``consolidation.account``), sem depender dele e sem o
escopo de consolidação financeira (períodos, taxas de câmbio): aqui é apenas o
mapeamento. Quem tem o Enterprise encontra o mesmo vocabulário.

Este módulo define o cadastro e a resolução (``plan.resolve(conta)``); quem o
consome são a exportação contábil e, futuramente, o SPED Contábil.
