{
    "name": "Helpdesk Description Optimizer",
    "version": "16.0.1.0.0",
    "category": "Tools",
    "summary": "Otimiza parsing e renderização do campo description",
    "depends": ["ag_helpdesk", "queue_job"],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_reprocess_wizard.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "helpdesk_description_optimizer/static/src/js/description_optimizer.js",
        ],
    },
    "installable": True,
    "license": "LGPL-3",
    "author": "KMEE",
}
