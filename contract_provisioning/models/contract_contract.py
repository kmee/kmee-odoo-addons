# Copyright 2024 Luis Miléo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ContractContract(models.Model):
    _inherit = "contract.contract"

    provisioning_periods = fields.Integer(
        string="Provisioning Periods",
        default=0,
        help="""Users can configure how many contracts be draft invoiced in advance
            for multiple periods, ensuring that invoices are generated proactively"""
    )

    provision_journal_id = fields.Many2one(
        'account.journal',
        string="Provision Journal",
        help="Journal to be used for prepaid invoices."
    )

    def _prepare_recurring_invoices_values(self, date_ref=False):
        invoices_values = super()._prepare_recurring_invoices_values(date_ref)
        if not invoices_values:
            return invoices_values

        for contract in self:
            provisioning_periods = contract.provisioning_periods
            if provisioning_periods > 0:
                contract_lines = contract.contract_line_ids
                if not contract_lines:
                    continue
                
                for _ in range(provisioning_periods - 1):
                    for line in contract_lines:
                        line._update_recurring_next_date()
                    new_invoices = super()._prepare_recurring_invoices_values()
                    for invoice in new_invoices:
                        invoice['journal_id'] = contract.provision_journal_id.id
                        invoice['provision_invoice'] = True
                        for line in invoice.get('invoice_line_ids', []):
                            line[2]['account_id'] = self.env.ref('account.data_account_provision').id
                    invoices_values.extend(new_invoices)
        
        return invoices_values


class AccountMove(models.Model):
    _inherit = "account.move"

    provision_invoice = fields.Boolean(
        string="Provision Invoice",
        help="Indicates if this invoice is a provision."
    )

    def process_provisioned_invoice(self):
        for move in self:
            if move.provision_invoice and move.state == 'posted':
                new_move_vals = move.copy_data()[0]
                new_move_vals['journal_id'] = move.contract_id.journal_id.id
                new_move_vals['provision_invoice'] = False
                for line in new_move_vals.get('line_ids', []):
                    if line[2]['account_id'] == self.env.ref('account.data_account_provision').id:
                        line[2]['account_id'] = move.partner_id.property_account_receivable_id.id
                self.create(new_move_vals)


# Algumas considerações para terminarmos esse módulo:

# 1 - Lançar em um diário separado;
# 2 - Quando for o mês corrente trocar para o diário padrão e a conta correta de clientes / fornecedores;
# 3 - Criar a fatura com uma conta de provisão em vez da de clientes / fornecedores;
# 4 - Marcar a fatura (account.move) com um booleano que ela é uma provisão, para facilitar os relatórios;
# 5 - Se a fatura de provisão já estiver confirmada, criar um cópia dela com o diário e conta correta,
#  mas ajustar o lançamento contábil tirando o valor de provisão e jogando em clientes.