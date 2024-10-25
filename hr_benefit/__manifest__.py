# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Hr Benefit",
    "summary": """
        Hr Benefit""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-private-addons",
    "depends": [
        "hr_contract",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_contract.xml",
        "views/hr_benefit_type.xml",
    ],
}
