# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Folha de Pagamento Brasileira",
    "summary": "Folha de pagamento brasileira com INSS, IRRF, FGTS e verbas CLT",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE,Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "category": "Human Resources",
    "depends": [
        "payroll",
        "l10n_br_hr",
        "l10n_br_hr_contract",
        # Fonte única do REGIME TRIBUTÁRIO na localização
        # (res.company.tax_framework / profit_calculation), do qual dependem
        # as rubricas patronais: no Simples Nacional dos anexos I, II, III e V
        # a folha não gera CPP/RAT/terceiros. Ver models/res_company.py.
        "l10n_br_fiscal",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/l10n_br.hr.payroll.inss.faixa.csv",
        "data/l10n_br.hr.payroll.irrf.faixa.csv",
        "data/l10n_br.hr.payroll.irrf.redutor.csv",
        "data/l10n_br.hr.payroll.sal.familia.faixa.csv",
        "data/l10n_br.hr.payroll.irrf.dependente.csv",
        "data/l10n_br.hr.payroll.cprb.transicao.csv",
        "data/hr_salary_rule_category_data.xml",
        "data/hr_salary_rule_data.xml",
        "data/hr_payroll_structure_data.xml",
        "data/hr_payroll_structure_encargos_data.xml",
        "views/fiscal_tables_views.xml",
        "views/res_company_views.xml",
        "views/hr_employee_views.xml",
        "views/hr_contract_views.xml",
        "views/hr_payslip_views.xml",
    ],
    "demo": [
        "demo/resource_calendar_payroll_demo.xml",
        "demo/hr_employee_payroll_demo.xml",
        "demo/hr_contract_payroll_demo.xml",
        "demo/hr_payslip_demo.xml",
        "demo/hr_payslip_run_demo.xml",
        "demo/res_company_regime_demo.xml",
        "demo/hr_employee_regime_demo.xml",
        "demo/hr_contract_regime_demo.xml",
        "demo/hr_payslip_regime_demo.xml",
    ],
    "installable": True,
    "auto_install": False,
}
