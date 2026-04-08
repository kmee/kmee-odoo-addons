{
    "name": "Project Kanban Multilevel",
    "version": "18.0.1.0.0",
    "category": "Project",
    "summary": "Kanban multinível com Initiatives, Swimlanes, Sub-colunas e WIP Limits",
    "description": """
        Módulo que implementa Kanban multinível no Project, inspirado no
        Businessmap/Kanbanize. Adiciona Initiatives Workflow, Swimlanes,
        Sub-colunas, WIP Limits e Cards compactos ao módulo nativo de projetos.
    """,
    "author": "Kanban Multilevel Team",
    "license": "LGPL-3",
    "depends": ["project"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/project_kanban_swimlane_views.xml",
        "views/project_task_type_views.xml",
        "views/project_task_views.xml",
        "views/project_project_views.xml",
        "views/project_portfolio_views.xml",
        "views/project_project_views_portfolio.xml",
        "views/project_analytics_views.xml",
        "wizard/swimlane_template_wizard_views.xml",
        "wizard/copy_swimlanes_wizard_views.xml",
    ],
    "demo": [
        "data/demo_data.xml",
        "data/demo_portfolio.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "project_kanban_multilevel/static/src/views/kanban_multilevel/**/*.js",
            "project_kanban_multilevel/static/src/views/kanban_multilevel/**/*.xml",
            "project_kanban_multilevel/static/src/views/kanban_multilevel/**/*.scss",
        ],
    },
    "installable": True,
    "application": False,
}
