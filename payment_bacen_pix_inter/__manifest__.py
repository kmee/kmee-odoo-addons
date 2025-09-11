{
    "name": "Banco Inter PIX",
    "version": "1.0",
    "category": "Accounting/Payment",
    "summary": "Integração PIX Banco Inter",
    "description": "Criação de cobranças PIX pelo Banco Inter",
    "depends": ["payment_bacen_pix"],
    "data": [
        "data/payment_provider.xml",
        "views/payment_provider_view_pix_inter.xml",
        "views/templates_pix_inter.xml",
        # "security/ir.model.access.csv"
    ],
    "installable": True,
    "application": False
}
