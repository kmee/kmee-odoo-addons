import json

from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    swimlane_id = fields.Many2one(
        "project.kanban.swimlane",
        string="Swimlane",
        tracking=True,
    )
    sub_stage = fields.Selection(
        [("doing", "Fazendo"), ("done", "Feito")],
        string="Sub-estágio",
        default="doing",
        tracking=True,
    )
    card_size = fields.Integer(
        string="Pontos (tamanho)",
        default=1,
    )
    is_blocked = fields.Boolean(
        string="Bloqueado",
        default=False,
        tracking=True,
    )
    blocked_reason = fields.Text(
        string="Motivo do bloqueio",
    )
    stage_entered_date = fields.Datetime(
        string="Entrada no estágio",
        default=fields.Datetime.now,
    )
    aging_days = fields.Integer(
        string="Aging (dias)",
        compute="_compute_aging_days",
        store=True,
    )
    is_initiative = fields.Boolean(
        string="É Initiative",
        compute="_compute_is_initiative",
        store=True,
    )
    child_progress_data = fields.Text(
        string="Dados de progresso filhos",
        compute="_compute_child_progress_data",
    )
    date_in_progress = fields.Datetime(
        string="Entrada em progresso",
    )
    date_done = fields.Datetime(
        string="Data de conclusão",
    )
    lead_time_days = fields.Integer(
        string="Lead Time (dias)",
        compute="_compute_lead_cycle_time",
        store=True,
    )
    cycle_time_days = fields.Integer(
        string="Cycle Time (dias)",
        compute="_compute_lead_cycle_time",
        store=True,
    )

    @api.depends("parent_id", "child_ids")
    def _compute_is_initiative(self):
        for task in self:
            task.is_initiative = not task.parent_id and bool(task.child_ids)

    @api.depends("stage_entered_date")
    def _compute_aging_days(self):
        now = fields.Datetime.now()
        for task in self:
            if task.stage_entered_date:
                delta = now - task.stage_entered_date
                task.aging_days = delta.days
            else:
                task.aging_days = 0

    @api.depends("child_ids.stage_id", "child_ids.stage_id.area_type")
    def _compute_child_progress_data(self):
        for task in self:
            if not task.child_ids:
                task.child_progress_data = "[]"
                continue
            data = []
            for child in task.child_ids:
                data.append(
                    {
                        "id": child.id,
                        "name": child.name,
                        "stage_name": child.stage_id.name or "",
                        "area_type": child.stage_id.area_type or "requested",
                    }
                )
            task.child_progress_data = json.dumps(data)

    @api.depends("create_date", "date_in_progress", "date_done")
    def _compute_lead_cycle_time(self):
        for task in self:
            if task.date_done and task.create_date:
                task.lead_time_days = (task.date_done - task.create_date).days
            else:
                task.lead_time_days = 0
            if task.date_done and task.date_in_progress:
                task.cycle_time_days = (
                    task.date_done - task.date_in_progress
                ).days
            else:
                task.cycle_time_days = 0

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            if "stage_entered_date" not in vals:
                vals["stage_entered_date"] = now
            # Set analytics dates based on initial stage
            if vals.get("stage_id"):
                stage = self.env["project.task.type"].browse(vals["stage_id"])
                if stage.area_type == "progress" and not vals.get("date_in_progress"):
                    vals["date_in_progress"] = now
                if stage.area_type == "done" and not vals.get("date_done"):
                    vals["date_done"] = now
                    if not vals.get("date_in_progress"):
                        vals["date_in_progress"] = now
        return super().create(vals_list)

    def write(self, vals):
        stage_changed = "stage_id" in vals
        sub_stage_changed = "sub_stage" in vals

        # Reset sub_stage when stage changes
        if stage_changed and "sub_stage" not in vals:
            vals["sub_stage"] = "doing"

        # Update stage_entered_date when stage or sub_stage changes
        if stage_changed or sub_stage_changed:
            vals["stage_entered_date"] = fields.Datetime.now()

        # Track analytics dates — collect info before super() but apply after
        analytics_area = False
        if stage_changed:
            new_stage = self.env["project.task.type"].browse(vals["stage_id"])
            analytics_area = new_stage.area_type
            if analytics_area == "done":
                vals["date_done"] = fields.Datetime.now()
            elif any(task.date_done for task in self):
                vals["date_done"] = False

        result = super().write(vals)

        # Post-write: set date_in_progress only for tasks that need it
        if stage_changed and analytics_area in ("progress", "done"):
            now = fields.Datetime.now()
            tasks_needing = self.filtered(lambda t: not t.date_in_progress)
            if tasks_needing:
                super(ProjectTask, tasks_needing).write(
                    {"date_in_progress": now}
                )

        # Log WIP violation if stage changed
        if stage_changed:
            self._check_wip_violation()

        return result

    def _check_wip_violation(self):
        """Check if moving tasks caused a WIP limit violation and log it."""
        for task in self:
            stage = task.stage_id
            if not stage or not stage.wip_limit:
                continue
            project = task.project_id
            if not project:
                continue
            # Count tasks in this stage for this project
            domain = [
                ("stage_id", "=", stage.id),
                ("project_id", "=", project.id),
            ]
            if stage.wip_limit_type == "size":
                tasks_in_stage = self.env["project.task"].search(domain)
                current = sum(tasks_in_stage.mapped("card_size"))
            else:
                current = self.env["project.task"].search_count(domain)

            if current > stage.wip_limit:
                task.message_post(
                    body=(
                        f"⚠️ WIP limit excedido no estágio "
                        f"'{stage.name}': {current}/{stage.wip_limit}"
                    ),
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                )

    @api.model
    def _cron_recompute_aging(self):
        """Daily cron to recompute aging_days for all tasks with stage_entered_date."""
        tasks = self.search([("stage_entered_date", "!=", False)])
        tasks._compute_aging_days()
