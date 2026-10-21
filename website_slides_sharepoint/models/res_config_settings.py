from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sharepoint_tenant_id = fields.Char(
        string="Microsoft Tenant ID",
        config_parameter="website_slides_sharepoint.tenant_id",
        help="Directory (tenant) ID of the Azure AD application used to read "
        "SharePoint files.",
    )
    sharepoint_client_id = fields.Char(
        string="Microsoft Client ID",
        config_parameter="website_slides_sharepoint.client_id",
        help="Application (client) ID of the Azure AD application.",
    )
    sharepoint_client_secret = fields.Char(
        string="Microsoft Client Secret",
        config_parameter="website_slides_sharepoint.client_secret",
        help="Client secret of the Azure AD application. The application needs the "
        "'Files.Read.All' and 'Sites.Read.All' application permissions, granted "
        "with admin consent.",
    )
    sharepoint_delivery_mode = fields.Selection(
        selection=[
            ("redirect", "Redirect to Microsoft (recommended)"),
            ("proxy", "Stream through Odoo"),
        ],
        string="SharePoint Delivery",
        default="redirect",
        config_parameter="website_slides_sharepoint.delivery_mode",
        help="How the SharePoint content reaches the attendee:\n"
        "* Redirect: Odoo answers with a redirection to a short lived "
        "pre-authenticated Microsoft URL. The media never transits through Odoo, "
        "which keeps the workers free.\n"
        "* Proxy: Odoo downloads the content and streams it to the attendee. "
        "Hides the Microsoft URL but consumes a worker for the whole playback.",
    )
