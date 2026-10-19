import base64
import logging
from datetime import datetime, timedelta

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
LOGIN_ROOT = "https://login.microsoftonline.com"
DEFAULT_TIMEOUT = 15

# Parameters holding the Azure AD application credentials.
PARAM_TENANT = "website_slides_sharepoint.tenant_id"
PARAM_CLIENT_ID = "website_slides_sharepoint.client_id"
PARAM_CLIENT_SECRET = "website_slides_sharepoint.client_secret"
# Cached application token (shared by all workers).
PARAM_TOKEN = "website_slides_sharepoint.access_token"
PARAM_TOKEN_EXPIRY = "website_slides_sharepoint.access_token_expiry"


class MsGraphClient(models.AbstractModel):
    """Thin Microsoft Graph client used to read SharePoint / OneDrive files.

    Authentication uses the OAuth2 *client credentials* flow, so the Odoo
    server talks to Graph with its own identity: no Microsoft session is
    required on the visitor side. This is what makes it possible to serve
    SharePoint content to anonymous eLearning attendees, something the
    SharePoint ``embed.aspx`` iframe cannot do.
    """

    _name = "ms.graph.client"
    _description = "Microsoft Graph Client"

    # ------------------------------------------------------------------
    # Credentials & token
    # ------------------------------------------------------------------

    @api.model
    def _get_credentials(self):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        credentials = {
            "tenant_id": (get_param(PARAM_TENANT) or "").strip(),
            "client_id": (get_param(PARAM_CLIENT_ID) or "").strip(),
            "client_secret": (get_param(PARAM_CLIENT_SECRET) or "").strip(),
        }
        if not all(credentials.values()):
            raise UserError(
                _(
                    "The Microsoft 365 integration is not configured. Please set the "
                    "Tenant ID, Application (client) ID and Client Secret in "
                    "Website > Configuration > Settings > eLearning."
                )
            )
        return credentials

    @api.model
    def _is_configured(self):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        return all(
            get_param(param)
            for param in (PARAM_TENANT, PARAM_CLIENT_ID, PARAM_CLIENT_SECRET)
        )

    @api.model
    def _get_access_token(self):
        """Return a valid application token, reusing the cached one when possible."""
        params = self.env["ir.config_parameter"].sudo()
        token = params.get_param(PARAM_TOKEN)
        expiry = params.get_param(PARAM_TOKEN_EXPIRY)
        if token and expiry:
            try:
                if datetime.utcnow() < datetime.fromisoformat(expiry):
                    return token
            except ValueError:
                _logger.warning(
                    "Corrupted Microsoft Graph token expiry %r, fetching a new token.",
                    expiry,
                )

        credentials = self._get_credentials()
        try:
            response = requests.post(
                "%s/%s/oauth2/v2.0/token" % (LOGIN_ROOT, credentials["tenant_id"]),
                data={
                    "grant_type": "client_credentials",
                    "client_id": credentials["client_id"],
                    "client_secret": credentials["client_secret"],
                    "scope": "https://graph.microsoft.com/.default",
                },
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            _logger.warning("Could not obtain a Microsoft Graph token: %s", error)
            raise UserError(
                _(
                    "Could not authenticate against Microsoft 365. Please check the "
                    "Tenant ID, Application (client) ID and Client Secret."
                )
            ) from error

        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise UserError(_("Microsoft 365 did not return an access token."))

        # Renew slightly before the real expiry to absorb clock skew.
        expires_in = int(payload.get("expires_in", 3600))
        expiry = datetime.utcnow() + timedelta(seconds=max(expires_in - 300, 60))
        params.set_param(PARAM_TOKEN, token)
        params.set_param(PARAM_TOKEN_EXPIRY, expiry.isoformat())
        return token

    @api.model
    def _clear_token_cache(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param(PARAM_TOKEN, False)
        params.set_param(PARAM_TOKEN_EXPIRY, False)

    # ------------------------------------------------------------------
    # Low level request
    # ------------------------------------------------------------------

    @api.model
    def _request(self, endpoint, params=None, allow_redirects=True, retry=True):
        """Perform a GET request on the Graph API.

        :param str endpoint: path relative to the Graph root (e.g. ``/shares/u!xxx``)
        :param bool allow_redirects: set to False to capture the pre-authenticated
            ``Location`` of ``/content`` endpoints instead of downloading the file.
        :param bool retry: retry once with a fresh token on 401 (token revoked).
        :return: the :class:`requests.Response`
        """
        token = self._get_access_token()
        try:
            response = requests.get(
                "%s%s" % (GRAPH_ROOT, endpoint),
                headers={"Authorization": "Bearer %s" % token},
                params=params,
                timeout=DEFAULT_TIMEOUT,
                allow_redirects=allow_redirects,
            )
        except requests.exceptions.RequestException as error:
            _logger.warning("Microsoft Graph request failed on %s: %s", endpoint, error)
            raise UserError(
                _("Could not reach Microsoft 365. Please try again later.")
            ) from error

        if response.status_code == 401 and retry:
            self._clear_token_cache()
            return self._request(
                endpoint, params=params, allow_redirects=allow_redirects, retry=False
            )
        if response.status_code in (403, 404):
            raise UserError(
                _(
                    "The file could not be found on SharePoint, or the Odoo "
                    "application does not have permission to read it. Make sure the "
                    "Azure AD application has the 'Files.Read.All' and "
                    "'Sites.Read.All' application permissions with admin consent."
                )
            )
        if response.status_code >= 400:
            _logger.warning(
                "Microsoft Graph returned %s on %s: %s",
                response.status_code,
                endpoint,
                response.text[:500],
            )
            raise UserError(
                _("Microsoft 365 returned an error (%s).", response.status_code)
            )
        return response

    # ------------------------------------------------------------------
    # High level helpers
    # ------------------------------------------------------------------

    @api.model
    def _encode_share_url(self, url):
        """Encode a sharing URL into the token expected by ``/shares/{id}``.

        See https://learn.microsoft.com/en-us/graph/api/shares-get
        """
        encoded = base64.b64encode(url.encode("utf-8")).decode("ascii")
        return "u!" + encoded.rstrip("=").replace("/", "_").replace("+", "-")

    @api.model
    def get_drive_item(self, share_url):
        """Resolve any SharePoint / OneDrive URL into its driveItem metadata.

        Works with sharing links (``/:v:/s/...``), ``stream.aspx`` links and
        direct file URLs, which is why we do not try to parse them ourselves.

        :return: dict with at least ``id``, ``name``, ``parentReference.driveId``
        """
        response = self._request(
            "/shares/%s/driveItem" % self._encode_share_url(share_url),
            params={
                "$select": "id,name,size,file,video,image,webUrl,parentReference",
            },
        )
        item = response.json()
        if not item.get("id") or not item.get("parentReference", {}).get("driveId"):
            raise UserError(
                _("Microsoft 365 did not return a usable file for this link.")
            )
        return item

    @api.model
    def get_content_url(self, drive_id, item_id, as_pdf=False):
        """Return a short lived pre-authenticated URL for the file content.

        :param bool as_pdf: ask Graph to convert the file (Word, Excel,
            PowerPoint...) to PDF on the fly.
        :return: str URL, valid for about one hour, or False when unavailable.
        """
        params = {"format": "pdf"} if as_pdf else None
        response = self._request(
            "/drives/%s/items/%s/content" % (drive_id, item_id),
            params=params,
            allow_redirects=False,
        )
        return response.headers.get("Location") or False

    @api.model
    def get_content(self, drive_id, item_id, as_pdf=False):
        """Download the file content as bytes (use sparingly, no streaming)."""
        params = {"format": "pdf"} if as_pdf else None
        response = self._request(
            "/drives/%s/items/%s/content" % (drive_id, item_id), params=params
        )
        return response.content

    @api.model
    def get_thumbnail_url(self, drive_id, item_id, size="large"):
        """Return the URL of a generated thumbnail, or False when there is none."""
        try:
            response = self._request(
                "/drives/%s/items/%s/thumbnails" % (drive_id, item_id)
            )
        except UserError:
            return False
        thumbnails = response.json().get("value") or []
        if not thumbnails:
            return False
        return thumbnails[0].get(size, {}).get("url") or False
