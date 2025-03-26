# Copyright 2021 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Sale Commission Team",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "category": "Sales",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "depends": ["sale_commission", "sale", "sales_team", "sale_commission_salesman"],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_team.xml",
        "views/res_partner.xml",
        "data/commission_rule_data.xml",
    ],
    "demo": [],
}
