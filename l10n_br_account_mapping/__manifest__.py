# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Planos de Contas de Destino",
    "summary": "Mapeia as contas do Odoo para planos de contas externos: o "
    "plano do escritorio de contabilidade e o plano referencial da RFB",
    "version": "16.0.1.0.0",
    "category": "Localisation",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["mileo"],
    "development_status": "Beta",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_mapping.xml",
    ],
    "demo": ["demo/account_mapping_demo.xml"],
    "installable": True,
}
