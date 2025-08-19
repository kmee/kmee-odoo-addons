{
    "name": "Product Configurator Quantity",
    "version": "16.0.1.0.0",
    "author": "KMEE",
    "license": "AGPL-3",
    "depends": ["product_configurator", "product_configurator_mrp"],
    "maintainers": ["andre"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_view.xml",
        "views/product_attribute_view.xml",
        "wizard/product_configurator_view.xml",
        "views/product_config_view.xml",
        "views/attribute_value_qty_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
