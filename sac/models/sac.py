# -*- coding: utf-8 -*-
# Copyright 2018 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import (division, print_function, unicode_literals,
                        absolute_import)

from odoo import api, fields, models, _


AVAILABLE_RATING = [
    ('0', '0'),
    ('1', '1'),
    ('2', '2'),
    ('3', '3'),
    ('4', '4'),
    ('5', '5 '),
]


class Sac(models.Model):

    _name = b'sac'
    _description = 'Serviço de atendimento ao consumidor'
    _inherit = ['mail.thread', 'ir.needaction_mixin',
                'utm.mixin', 'base.kanban.abstract']

    @api.depends('create_date')
    def _compute_create_date(self):
        for record in self:
            # TODO: Tratar o fuso horário
            record.create_date_date = record.create_date

    @api.multi
    @api.depends('name', 'customer_name')
    def _compute_display_name(self):
        for r in self:
            if r.customer_name:
                r.display_name = '[%s] %s' % (r.name, r.customer_name)
            else:
                r.display_name = r.name

    display_name = fields.Char(
        "Name",
        compute="_compute_display_name",
        readonly=True,
        store=True
    )
    active = fields.Boolean(
        readonly=True,
        default=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        index=True,
        default=lambda self: self.env.user.company_id.id
    )
    name = fields.Char(
        string='Order Reference',
        required=True,
        copy=False,
        readonly=True,
        # states={'draft': [('readonly', False)]},
        index=True,
        default=lambda self: _('New')
    )
    create_date = fields.Datetime(
        string='Creation Date',
        readonly=True,
        index=True,
        help="Date on which sac is created."
    )
    create_date_date = fields.Date(
        compute='_compute_create_date',
    )
    # create_date_hour = fields.Datetime(
    #     string='Creation Date',
    #     readonly=True,
    #     index=True,
    #     help="Date on which sac is created."
    # )
    customer_name = fields.Char(
        string='Customer Name',
        required=True,
        track_visibility='onchange',
    )
    cnpj_cpf = fields.Char(
        string='CNPJ/CPF',
        size=14,
        track_visibility='onchange',
    )
    email_from = fields.Char(
        string='Email',
        track_visibility='onchange',
    )
    email_cc = fields.Char(
        string='Email CC',
        track_visibility='onchange',
    )
    phone = fields.Char(
        string='Phone',
        track_visibility='onchange',
    )
    phone2 = fields.Char(
        string='Phone 2',
        track_visibility='onchange',
    )
    zip = fields.Char(
        string='Zip',
    )
    street = fields.Char(
        string='Street',
        track_visibility='onchange',
    )
    number = fields.Char(
        string='Nº',
        track_visibility='onchange',
    )
    district = fields.Char(
        string='Bairro',
        track_visibility='onchange',
    )
    street2 = fields.Char(
        string='Complemento',
    )
    # country_id = fields.Many2one(
    #     string='Pais',
    #     comodel_name='res.country',
    #     default=lambda self: self.env.ref('base.br'),
    # )
    state_id = fields.Many2one(
        string='Estado',
        comodel_name='res.country.state',
        domain=lambda self: [
            ('country_id', '=', self.env.ref('base.br').id)
        ],
    )
    l10n_br_city_id = fields.Many2one(
        comodel_name='l10n_br_base.city',
        string='Municipio',
        domain="[('state_id','=',state_id)]"
    )
    product_id = fields.Many2one(
        string='Produto',
        comodel_name='product.product',
        track_visibility='onchange',
        domain="[('sale_ok', '=', True),('sac_ok', '=', True)]"
    )
    qty = fields.Integer(
        string='Quantidade',
        track_visibility='onchange',
        default=1,
    )
    reason_id = fields.Many2one(
        comodel_name='sac.reason',
        string='Motivo',
        track_visibility='onchange',
    )
    type_id = fields.Many2one(
        comodel_name='sac.type',
        string='Tipo de reclamação',
        track_visibility='onchange',
    )
    bank_id = fields.Many2one(
        string='Banco',
        comodel_name='res.bank',
        track_visibility='onchange',
    )
    bank_branch = fields.Char(
        string='Ag c/ digito',
        track_visibility='onchange',
    )
    bank_account = fields.Char(
        string='Conta c/ digito',
        track_visibility='onchange',
    )
    bank_type = fields.Selection(
        string='Tipo',
        selection=[
            ('poupanca', 'Poupança'),
            ('conta_corrente', 'Conta corrente'),
        ],
        track_visibility='onchange',
    )
    tracking_code = fields.Char(
        string='Tracking Code',
        track_visibility='onchange',
    )
    send_date = fields.Datetime(
        string='Send date',
        index=True,
        track_visibility='onchange',
    )
    end_date = fields.Datetime(
        string='End Date',
        readonly=True,
        index=True,
        track_visibility='onchange',
    )
    lot = fields.Char(
        string='Lote',
        track_visibility='onchange',
    )
    due_date = fields.Date(
        string='Data de validade'
    )
    rating = fields.Selection(
        selection=AVAILABLE_RATING,
        string='Feedback',
        index=True,
        default=AVAILABLE_RATING[0][0],
        track_visibility='onchange',
    )
    message = fields.Text(
        string='Mensagem',
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(
                    force_company=vals['company_id']
                ).next_by_code('sac') or _('New')
            else:
                vals['name'] = \
                    self.env['ir.sequence'].next_by_code('sac') or _('New')
        result = super(Sac, self).create(vals)
        return result

    @api.multi
    def _track_template(self, tracking):
        res = super(Sac, self)._track_template(tracking)
        test_record = self[0]
        changes, tracking_value_ids = tracking[test_record.id]
        if 'stage_id' in changes and \
                test_record.stage_id.mail_template_id:
            res['stage_id'] = (
                test_record.stage_id.mail_template_id,
                {
                    'composition_mode': 'mass_mail'
                }
            )
        return res

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ Overrides mail_thread message_new that is called by the
        mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        # remove default author when going through the mail gateway.
        # Indeed we do not want to explicitly set user_id to False;
        # however we do not want the gateway user to be responsible
        # if no other responsible is
        # found.
        self = self.with_context(default_user_id=False)

        if custom_values is None:
            custom_values = {}
        defaults = {
            'customer_name':  msg_dict.get('subject') or _("Sem assunto"),
            'email_from': msg_dict.get('from'),
            'email_cc': msg_dict.get('cc'),
            # 'partner_id': msg_dict.get('author_id', False),
        }
        # if msg_dict.get('author_id'):
        #     defaults.update(self._onchange_partner_id_values(
        #     msg_dict.get('author_id')))
        # if msg_dict.get('priority') in dict(crm_stage.AVAILABLE_PRIORITIES):
        #     defaults['priority'] = msg_dict.get('priority')
        defaults.update(custom_values)
        return super(Sac, self).message_new(msg_dict, custom_values=defaults)

    #
    # @api.multi
    # def message_update(self, msg_dict, update_vals=None):
    #     """ Overrides mail_thread message_update that is called by
    #  the mailgateway
    #         through message_process.
    #         This method updates the document according to the email.
    #     """
    #     if update_vals is None:
    #         update_vals = {}
    #     if msg_dict.get('priority') in dict(crm_stage.AVAILABLE_PRIORITIES):
    #         update_vals['priority'] = msg_dict.get('priority')
    #     maps = {
    #         'revenue': 'planned_revenue',
    #         'probability': 'probability',
    #     }
    #     for line in msg_dict.get('body', '').split('\n'):
    #         line = line.strip()
    #         res = tools.command_re.match(line)
    #         if res and maps.get(res.group(1).lower()):
    #             key = maps.get(res.group(1).lower())
    #             update_vals[key] = res.group(2).lower()
    #     return super(Lead, self).message_update(msg_dict,
    #  update_vals=update_vals)
    #
    # @api.multi
    # def message_partner_info_from_emails(self, emails, link_mail=False):
    #     result = super(Lead, self).message_partner_info_from_emails(
    # emails, link_mail=link_mail)
    #     for partner_info in result:
    #         if not partner_info.get('partner_id') and (
    # self.partner_name or self.contact_name):
    #             emails = email_re.findall(partner_info['full_name'] or '')
    #             email = emails and emails[0] or ''
    #             if email and self.email_from and email.lower() ==
    # self.email_from.lower():
    #                 partner_info['full_name'] =
    # '%s <%s>' % (self.partner_name or self.contact_name, email)
    #                 break
    #     return result
