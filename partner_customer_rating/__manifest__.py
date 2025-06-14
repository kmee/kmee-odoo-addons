{
    'name': 'Customer Satisfaction Thermometer',
    'version': '16.0.1.0.0',
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    'depends': ['base', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/customer_rating_views.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'partner_customer_rating/static/src/css/customer_rating_styles.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
