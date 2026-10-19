Este módulo desativa a geração automática de faturas a partir das liquidações de
comissão. A fatura do agente é lançada manualmente, fora do Odoo ou no
financeiro, e o andamento é acompanhado na própria liquidação.

* Os métodos de criação de fatura (`action_invoice` e `make_invoices`) passam a
  retornar um erro explicando que o processo é manual;
* O menu de faturamento das liquidações é ocultado;
* A liquidação ganha o estado **Pago** e botões para marcar como faturada,
  paga, com exceção de fatura ou voltar para liquidada;
* Uma liquidação faturada pode ser cancelada, pois não existe fatura gerada
  pelo Odoo para ser desfeita.
