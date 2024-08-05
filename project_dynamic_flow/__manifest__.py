# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Project Dynamic Flow",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-private-addons",
    "depends": [
        "base_wip",
        "project",
        "project_parent",
        "project_parent_task_filter",
        "project_task_add_very_high",
        "project_timeline",
        "project_timeline_hr_timesheet",
        "project_type",
        "project_task_personal_stage_auto_fold",
        "project_task_default_stage",
        "project_task_code",
        "project_task_link",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/project_view.xml",
        "views/project_task.xml",
        "reports/task_throughput_report_views.xml",
    ],
}
