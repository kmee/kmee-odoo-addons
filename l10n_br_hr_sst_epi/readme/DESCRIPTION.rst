Controle de EPI segundo a NR-6, sobre a pilha de equipamentos pessoais da OCA.

A alocação, o ciclo de vida, a expiração por cron, a aprovação em camadas e a
baixa de estoque continuam sendo do ``hr_personal_equipment_request`` e do
``hr_employee_ppe``. Este módulo acrescenta o que a legislação brasileira exige:

* **Certificado de Aprovação (CA)** como entidade própria, com validade do
  fabricante, situação (vigente, a vencer, vencido) e cron de alerta. O número do
  CA é o que vai no campo ``docAval`` do S-2240.
* **Bloqueio da entrega de EPI com CA vencido na data da entrega**, e bloqueio da
  entrega de EPI sem CA informado. A pilha da OCA expira a alocação, não valida o
  certificado.
* **Vínculo do EPI ao fator de risco neutralizado**, que é o que permite ao
  S-2240 declarar a utilização e a eficácia do equipamento.
* **Assinatura eletrônica do trabalhador** no recebimento, admitida pela Portaria
  SIT 107/2009, e **motivo de troca ou devolução**.
* **Ficha de EPI em PDF** por trabalhador, com o histórico completo de entregas,
  para apresentar em fiscalização.
