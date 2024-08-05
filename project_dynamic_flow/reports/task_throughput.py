from psycopg2.extensions import AsIs

from odoo import fields, models, tools


class TaskThroughput(models.Model):
    """TaskThroughput"""

    _name = "task.throughput.report"
    _auto = False
    _description = "Task Throughput Analysis"
    _rec_name = "id"

    # user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)

    date = fields.Date(readonly=True)
    project_id = fields.Many2one("project.project", "Project", readonly=True)
    milestone_id = fields.Many2one("project.milestone", "Milestone", readonly=True)
    in_qty = fields.Integer("IN", readonly=True, default=0)
    out_qty = fields.Integer("OUT", readonly=True, default=0)

    def init(self):
        query = """
            SELECT
                row_number() OVER (ORDER BY date, project_id, milestone_id) AS id,
                date,
                project_id,
                milestone_id,
                in_qty,
                out_qty
            FROM (
                SELECT
                    DATE(create_date) AS date,
                    project_id,
                    milestone_id,
                    COUNT(id) AS in_qty,
                    0 AS out_qty
                FROM
                    project_task
                WHERE
                    active = 't'
                GROUP BY
                    DATE(create_date), project_id, milestone_id

                UNION ALL

                SELECT
                    DATE(date_end) AS date,
                    project_id,
                    milestone_id,
                    0 AS in_qty,
                    COUNT(id) AS out_qty
                FROM
                    project_task
                WHERE
                    active = 't' AND state = 'done'
                GROUP BY
                    DATE(date_end), project_id, milestone_id
            ) subquery
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute(
            "CREATE OR REPLACE VIEW %s AS (%s)", (AsIs(self._table), AsIs(query))
        )
