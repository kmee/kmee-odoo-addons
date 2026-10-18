from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    @api.depends("create_date", "date_closed", "probability", "active")
    def _compute_sales_cycle(self):
        for lead in self:
            if lead.create_date and lead.date_closed:
                delta = lead.date_closed - lead.create_date
                # Oportunidade ganha (probability = 100)
                if lead.probability == 100:
                    lead.won_sales_cycle_days = delta.days
                    lead.lost_sales_cycle_days = 0
                # Oportunidade perdida (probability = 0 ou inativa)
                elif lead.probability == 0 or not lead.active:
                    lead.lost_sales_cycle_days = delta.days
                    lead.won_sales_cycle_days = 0
                else:
                    lead.won_sales_cycle_days = 0
                    lead.lost_sales_cycle_days = 0
            else:
                lead.won_sales_cycle_days = 0
                lead.lost_sales_cycle_days = 0

    @api.depends("date_last_stage_update")
    def _compute_days_in_current_stage(self):
        today = fields.Date.today()
        for lead in self:
            if lead.date_last_stage_update:
                last_update_date = fields.Date.from_string(lead.date_last_stage_update)
                lead.days_in_current_stage = (today - last_update_date).days
            else:
                lead.days_in_current_stage = 0

    @api.depends("activity_ids.create_date")
    def _compute_last_activity_date(self):
        for lead in self:
            activities = lead.activity_ids.sorted("create_date", reverse=True)
            lead.last_activity_date = activities[0].create_date if activities else False

    @api.depends("last_activity_date")
    def _compute_days_since_last_activity(self):
        today = fields.Datetime.now()
        for lead in self:
            if lead.last_activity_date:
                delta = today - lead.last_activity_date
                lead.days_since_last_activity = delta.days
            else:
                lead.days_since_last_activity = 0

    @api.depends("probability", "expected_revenue")
    def _compute_weighted_revenue(self):
        for lead in self:
            lead.weighted_revenue = (
                lead.expected_revenue * (lead.probability / 100)
                if lead.probability
                else 0
            )

    @api.depends("activity_ids")
    def _compute_outreach_count(self):
        for lead in self:
            lead.outreach_count = len(lead.activity_ids)

    @api.depends("calendar_event_ids")
    def _compute_meeting_count(self):
        for lead in self:
            lead.meeting_count = len(lead.calendar_event_ids)

    # Campos para automação
    last_activity_date = fields.Datetime(
        string="Data da Última Atividade",
        compute="_compute_last_activity_date",
        store=True,
    )
    days_since_last_activity = fields.Integer(
        string="Dias Desde Última Atividade",
        compute="_compute_days_since_last_activity",
    )

    weighted_revenue = fields.Monetary(
        string="Receita Ponderada",
        compute="_compute_weighted_revenue",
        store=True,
        currency_field="company_currency",
    )

    days_in_current_stage = fields.Integer(
        string="Dias no Estágio Atual",
        compute="_compute_days_in_current_stage",
        help="Número de dias que o lead está no estágio atual",
        store=True,
    )

    outreach_count = fields.Integer(
        string="Número de Atividades",
        compute="_compute_outreach_count",
        store=True,
        readonly=False,
        help="Número total de atividades registradas",
    )

    meeting_count = fields.Integer(
        string="Número de Reuniões",
        compute="_compute_meeting_count",
        store=True,
        readonly=False,
        help="Número total de reuniões agendadas",
    )

    # Campos para análise
    source_channel = fields.Selection(
        [
            ("inbound_call", "Inbound – Ligação Recebida"),
            ("inbound_internal", "Inbound - Direcionamento Interno"),
            ("inbound_organic", "Inbound - Orgânico/Desconhecido"),
            ("outbound_segmented", "Outbound - Prospecção Segmentada"),
            ("outbound_events", "Outbound – Eventos"),
            ("migration_saraiva", "Migração Saraiva"),
        ],
        string="Canal de Origem",
        default="inbound_call",
    )

    won_sales_cycle_days = fields.Integer(
        string="Dias até Ganhar",
        compute="_compute_sales_cycle",
        store=True,
        help="Número de dias desde a criação até ganhar a oportunidade",
    )

    lost_sales_cycle_days = fields.Integer(
        string="Dias até Perder",
        compute="_compute_sales_cycle",
        store=True,
        help="Número de dias desde a criação até perder a oportunidade",
    )

    # sdr_id = fields.Many2one(
    # 'res.users', string='SDR Responsável', domain=[('is_sdr', '=', True)])
    # ae_id = fields.Many2one(
    # 'res.users', string='AE Responsável', domain=[('is_ae', '=', True)])

    # qualification_date = fields.Datetime(string='Data de Qualificação')
    # discovery_date = fields.Datetime(string='Data de Descoberta')
    # proposal_date = fields.Datetime(string='Data de Proposta')
    # negotiation_date = fields.Datetime(string='Data de Negociação')
