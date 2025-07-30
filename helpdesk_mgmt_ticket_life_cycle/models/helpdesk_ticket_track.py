from odoo import api, fields, models


def display_duration(seconds, granularity=2):
    result = []

    intervals = (
        ("w", 604800),  # 60 * 60 * 24 * 7
        ("days", 86400),  # 60 * 60 * 24
        ("hours", 3600),  # 60 * 60
        ("min", 60),
        ("sec", 1),
    )
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip("s")
            result.append("{} {}".format(int(value), name))
    return ", ".join(result[:granularity])


class HelpdeskTicketTrack(models.Model):
    _inherit = "helpdesk.ticket"

    stage_duration_ids = fields.One2many(
        "helpdesk.ticket.stage.duration", "ticket_id", string="Stage Durations"
    )

    current_stage_total_duration = fields.Char(
        string="Total Time in Current Stage",
        compute="_compute_current_stage_total_duration",
    )

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super(HelpdeskTicketTrack, self).create(vals_list)
        for ticket in tickets:
            if ticket.stage_id:
                ticket.stage_duration_ids.create(
                    {
                        "ticket_id": ticket.id,
                        "stage_id": ticket.stage_id.id,
                        "team_id": ticket.team_id.id,
                        "start_date": fields.Datetime.now(),
                    }
                )
        return tickets

    def write(self, vals):
        res = super(HelpdeskTicketTrack, self).write(vals)
        if "stage_id" in vals:
            for ticket in self:
                previous_stage = ticket.stage_duration_ids.filtered(
                    lambda s: not s.end_date
                )
                if previous_stage:
                    previous_stage.end_date = fields.Datetime.now()
                ticket.stage_duration_ids.create(
                    {
                        "ticket_id": ticket.id,
                        "stage_id": vals["stage_id"],
                        "team_id": ticket.team_id.id,
                        "start_date": fields.Datetime.now(),
                    }
                )
        return res

    def _compute_current_stage_total_duration(self):
        for ticket in self:
            ticket.current_stage_total_duration = ""
            if ticket.stage_id:
                # Get all stage durations for the current stage
                stage_durations = ticket.stage_duration_ids.filtered(
                    lambda d: d.stage_id.id == ticket.stage_id.id
                )

                total_seconds = 0.0
                for duration in stage_durations:
                    if duration.start_date:
                        if duration.end_date:
                            # Duration is complete
                            duration_seconds = (
                                duration.end_date - duration.start_date
                            ).total_seconds()
                        else:
                            # Duration is still running - use current time
                            current_time = fields.Datetime.now()
                            duration_seconds = (
                                current_time - duration.start_date
                            ).total_seconds()
                        total_seconds += duration_seconds
                if total_seconds > 0:
                    ticket.current_stage_total_duration = display_duration(
                        total_seconds, 2
                    )


class HelpdeskTicketTrackStageDuration(models.Model):
    _name = "helpdesk.ticket.stage.duration"
    _description = "ticket Stage Duration"

    ticket_id = fields.Many2one(
        "helpdesk.ticket", string="ticket", required=True, ondelete="cascade"
    )
    stage_id = fields.Many2one("helpdesk.ticket.stage", string="Stage", required=True)
    team_id = fields.Many2one("helpdesk.ticket.team", string="Team", required=True)
    start_date = fields.Datetime(required=True)
    end_date = fields.Datetime()

    duration_seconds = fields.Float(
        string="Duration in Seconds", compute="_compute_duration_seconds", store=True
    )

    duration_display = fields.Char(
        string="Duration",
        compute="_compute_duration_display",
    )

    @api.depends("start_date", "end_date")
    def _compute_duration_seconds(self):
        for record in self:
            if record.start_date:
                if record.end_date:
                    # Duration is complete
                    duration = record.end_date - record.start_date
                    record.duration_seconds = duration.total_seconds()
                else:
                    # Duration is still running - calculate current duration
                    current_time = fields.Datetime.now()
                    duration = current_time - record.start_date
                    record.duration_seconds = duration.total_seconds()
            else:
                record.duration_seconds = 0.0

    @api.depends("duration_seconds")
    def _compute_duration_display(self):
        for record in self:
            if record.duration_seconds > 0:
                if record.end_date:
                    # Duration is complete
                    record.duration_display = display_duration(
                        record.duration_seconds, 4
                    )
                else:
                    # Duration is still running
                    record.duration_display = (
                        display_duration(record.duration_seconds, 4) + " (em andamento)"
                    )
            else:
                record.duration_display = ""
