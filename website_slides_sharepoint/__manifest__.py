{
    "name": "Website Slides - SharePoint / Microsoft 365",
    "summary": "Use SharePoint / OneDrive videos and documents as eLearning content",
    "version": "16.0.1.0.0",
    "category": "Website/eLearning",
    "author": "KMEE",
    "website": "https://github.com/KMEE/kmee-odoo-addons",
    "license": "AGPL-3",
    "depends": ["website_slides"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/slide_slide_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_slides_sharepoint/static/src/scss/slides_sharepoint.scss",
            "website_slides_sharepoint/static/src/js/slides_sharepoint_player.esm.js",
            "website_slides_sharepoint/static/src/xml/slides_sharepoint_player.xml",
            "website_slides_sharepoint/static/src/xml/slides_sharepoint_upload.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
}
