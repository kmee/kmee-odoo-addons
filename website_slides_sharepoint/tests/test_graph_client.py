# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from unittest.mock import patch

import requests

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

CLIENT = "odoo.addons.website_slides_sharepoint.models.ms_graph_client"
LOGGER = CLIENT


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, content=b""):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.content = content
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


@tagged("post_install", "-at_install")
class TestMsGraphClient(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.graph = cls.env["ms.graph.client"]
        cls.params = cls.env["ir.config_parameter"].sudo()

    def _configure(self):
        self.params.set_param("website_slides_sharepoint.tenant_id", " tenant ")
        self.params.set_param("website_slides_sharepoint.client_id", "client")
        self.params.set_param("website_slides_sharepoint.client_secret", "secret")

    def _token_response(self, token="tok", expires_in=3600):
        return FakeResponse(payload={"access_token": token, "expires_in": expires_in})

    def _cache_token(self, token="cached", delta=None):
        delta = delta or timedelta(hours=1)
        self.params.set_param("website_slides_sharepoint.access_token", token)
        self.params.set_param(
            "website_slides_sharepoint.access_token_expiry",
            (datetime.utcnow() + delta).isoformat(),
        )

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------
    def test_credentials_missing_raise_user_error(self):
        """Given no credentials, Then the client is not configured and asking
        for credentials raises a UserError."""
        for param in ("tenant_id", "client_id", "client_secret"):
            self.params.set_param("website_slides_sharepoint.%s" % param, False)
        self.assertFalse(self.graph._is_configured())
        with self.assertRaises(UserError):
            self.graph._get_credentials()

    def test_credentials_are_stripped_and_all_required(self):
        """Given all three credentials (one with spaces), Then they are
        returned stripped; with one missing the client is not configured."""
        self._configure()
        self.assertTrue(self.graph._is_configured())
        self.assertEqual(self.graph._get_credentials()["tenant_id"], "tenant")
        self.params.set_param("website_slides_sharepoint.client_secret", False)
        self.assertFalse(self.graph._is_configured())

    # ------------------------------------------------------------------
    # Token
    # ------------------------------------------------------------------
    def test_token_is_fetched_and_cached(self):
        """Given credentials and no cache, When asking for a token twice, Then
        Microsoft is called once and the cache keeps the token."""
        self._configure()
        with patch(
            CLIENT + ".requests.post", return_value=self._token_response()
        ) as post:
            first = self.graph._get_access_token()
            second = self.graph._get_access_token()
        self.assertEqual((first, second), ("tok", "tok"))
        post.assert_called_once()
        self.assertIn("/tenant/oauth2/v2.0/token", post.call_args.args[0])
        self.assertEqual(
            post.call_args.kwargs["data"]["grant_type"], "client_credentials"
        )
        self.assertEqual(
            self.params.get_param("website_slides_sharepoint.access_token"), "tok"
        )

    def test_token_expiry_keeps_a_safety_margin(self):
        """Given a token valid for 3600 s, Then the cached expiry is about 5
        minutes earlier; a very short token still gets at least 60 s."""
        self._configure()
        key = "website_slides_sharepoint.access_token_expiry"
        with patch(CLIENT + ".requests.post", return_value=self._token_response()):
            self.graph._get_access_token()
        delta = datetime.fromisoformat(self.params.get_param(key)) - datetime.utcnow()
        self.assertTrue(timedelta(seconds=3200) < delta < timedelta(seconds=3300))
        self.graph._clear_token_cache()
        with patch(
            CLIENT + ".requests.post", return_value=self._token_response(expires_in=10)
        ):
            self.graph._get_access_token()
        delta = datetime.fromisoformat(self.params.get_param(key)) - datetime.utcnow()
        self.assertTrue(timedelta(seconds=30) < delta <= timedelta(seconds=60))

    def test_valid_cached_token_is_reused_without_http(self):
        """Given a cached token not yet expired, Then no HTTP call is made."""
        self._cache_token("cached")
        with patch(CLIENT + ".requests.post") as post:
            self.assertEqual(self.graph._get_access_token(), "cached")
        post.assert_not_called()

    def test_expired_cached_token_is_renewed(self):
        """Given an expired cached token, Then a new one is requested."""
        self._configure()
        self._cache_token("old", delta=-timedelta(minutes=1))
        with patch(CLIENT + ".requests.post", return_value=self._token_response("new")):
            self.assertEqual(self.graph._get_access_token(), "new")

    @mute_logger(LOGGER)
    def test_corrupted_expiry_forces_renewal(self):
        """Given an unreadable expiry date, Then the cache is ignored and a new
        token is requested."""
        self._configure()
        self.params.set_param("website_slides_sharepoint.access_token", "old")
        self.params.set_param(
            "website_slides_sharepoint.access_token_expiry", "garbage"
        )
        with patch(CLIENT + ".requests.post", return_value=self._token_response("new")):
            self.assertEqual(self.graph._get_access_token(), "new")

    @mute_logger(LOGGER)
    def test_token_failures_become_user_errors(self):
        """Given an HTTP failure, an HTTP 401 or a payload without token, Then
        a UserError is raised and nothing is cached."""
        self._configure()
        failures = (
            {"side_effect": requests.ConnectionError("down")},
            {"return_value": FakeResponse(401)},
            {"return_value": FakeResponse(200, payload={})},
        )
        for kwargs in failures:
            with patch(CLIENT + ".requests.post", **kwargs):
                with self.assertRaises(UserError):
                    self.graph._get_access_token()
        self.assertFalse(
            self.params.get_param("website_slides_sharepoint.access_token")
        )

    def test_clear_token_cache(self):
        """Given a cached token, When the cache is cleared, Then it is gone."""
        self._cache_token()
        self.graph._clear_token_cache()
        self.assertFalse(
            self.params.get_param("website_slides_sharepoint.access_token")
        )
        self.assertFalse(
            self.params.get_param("website_slides_sharepoint.access_token_expiry")
        )

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------
    def test_request_sends_bearer_token_and_params(self):
        """Given a cached token, When requesting an endpoint, Then the Graph URL,
        bearer header and parameters are sent."""
        self._cache_token("cached")
        with patch(CLIENT + ".requests.get", return_value=FakeResponse()) as get:
            response = self.graph._request("/x", params={"a": 1}, allow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_args.args[0], "https://graph.microsoft.com/v1.0/x")
        kwargs = get.call_args.kwargs
        self.assertEqual(kwargs["headers"], {"Authorization": "Bearer cached"})
        self.assertEqual(kwargs["params"], {"a": 1})
        self.assertFalse(kwargs["allow_redirects"])

    def test_request_retries_once_with_fresh_token_on_401(self):
        """Given a revoked token (401), When requesting, Then the token cache is
        cleared and the request is retried once with a new token."""
        self._configure()
        self._cache_token("old")
        responses = [FakeResponse(401), FakeResponse(200)]
        with patch(CLIENT + ".requests.get", side_effect=responses) as get, patch(
            CLIENT + ".requests.post", return_value=self._token_response("new")
        ):
            response = self.graph._request("/x")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_count, 2)
        sent = [call.kwargs["headers"]["Authorization"] for call in get.call_args_list]
        self.assertEqual(sent, ["Bearer old", "Bearer new"])

    @mute_logger(LOGGER)
    def test_request_gives_up_after_the_retry(self):
        """Given a persistent 401, Then a single retry happens and a UserError
        is raised."""
        self._configure()
        self._cache_token("old")
        with patch(
            CLIENT + ".requests.get", return_value=FakeResponse(401)
        ) as get, patch(
            CLIENT + ".requests.post", return_value=self._token_response("new")
        ):
            with self.assertRaises(UserError):
                self.graph._request("/x")
        self.assertEqual(get.call_count, 2)

    @mute_logger(LOGGER)
    def test_request_errors_become_user_errors(self):
        """Given 403, 404, 500 or a network failure, Then a UserError is raised;
        the permission hint is only given for 403 and 404."""
        self._cache_token()
        messages = {}
        for status in (403, 404, 500):
            with patch(CLIENT + ".requests.get", return_value=FakeResponse(status)):
                with self.assertRaises(UserError) as caught:
                    self.graph._request("/x")
            messages[status] = caught.exception.args[0]
        self.assertIn("Files.Read.All", messages[403])
        self.assertEqual(messages[403], messages[404])
        self.assertIn("500", messages[500])
        with patch(CLIENT + ".requests.get", side_effect=requests.Timeout("slow")):
            with self.assertRaises(UserError):
                self.graph._request("/x")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def test_get_drive_item_requests_the_encoded_share(self):
        """Given a sharing URL, When resolving it, Then the /shares endpoint is
        called with the encoded token and the item is returned."""
        self._cache_token()
        item = {"id": "I1", "parentReference": {"driveId": "D1"}}
        with patch(
            CLIENT + ".requests.get", return_value=FakeResponse(payload=item)
        ) as get:
            result = self.graph.get_drive_item("https://contoso.sharepoint.com/x")
        self.assertEqual(result, item)
        endpoint = get.call_args.args[0]
        self.assertIn(
            "/shares/%s/driveItem"
            % self.graph._encode_share_url("https://contoso.sharepoint.com/x"),
            endpoint,
        )
        self.assertIn("$select", get.call_args.kwargs["params"])

    def test_get_drive_item_without_usable_data_raises(self):
        """Given an answer without item id or drive id, Then UserError."""
        self._cache_token()
        for payload in ({}, {"id": "I1"}, {"id": "I1", "parentReference": {}}):
            with patch(
                CLIENT + ".requests.get", return_value=FakeResponse(payload=payload)
            ):
                with self.assertRaises(UserError):
                    self.graph.get_drive_item("https://contoso.sharepoint.com/x")

    def test_get_content_url_captures_the_redirect_location(self):
        """Given a redirect answer, Then the Location header is the URL and
        redirects are not followed; without it the result is False."""
        self._cache_token()
        redirect = FakeResponse(302, headers={"Location": "https://pre.auth/file"})
        with patch(CLIENT + ".requests.get", return_value=redirect) as get:
            url = self.graph.get_content_url("D1", "I1")
        self.assertEqual(url, "https://pre.auth/file")
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        self.assertIsNone(get.call_args.kwargs["params"])
        self.assertIn("/drives/D1/items/I1/content", get.call_args.args[0])
        with patch(CLIENT + ".requests.get", return_value=FakeResponse(200)):
            self.assertFalse(self.graph.get_content_url("D1", "I1"))

    def test_pdf_conversion_is_requested_with_format_pdf(self):
        """Given as_pdf, Then Graph is asked for format=pdf, otherwise no
        format parameter is sent."""
        self._cache_token()
        redirect = FakeResponse(302, headers={"Location": "https://pre.auth/x"})
        with patch(CLIENT + ".requests.get", return_value=redirect) as get:
            self.graph.get_content_url("D1", "I1", as_pdf=True)
        self.assertEqual(get.call_args.kwargs["params"], {"format": "pdf"})
        with patch(
            CLIENT + ".requests.get", return_value=FakeResponse(content=b"%PDF")
        ) as get:
            content = self.graph.get_content("D1", "I1", as_pdf=True)
        self.assertEqual(content, b"%PDF")
        self.assertEqual(get.call_args.kwargs["params"], {"format": "pdf"})
        self.assertTrue(get.call_args.kwargs["allow_redirects"])

    def test_thumbnail_url_variants(self):
        """Given thumbnails, Then the requested size is returned; no thumbnail,
        a missing size or a Graph error give False."""
        self._cache_token()
        payload = {
            "value": [{"large": {"url": "https://t/large"}, "small": {"url": "s"}}]
        }
        with patch(
            CLIENT + ".requests.get", return_value=FakeResponse(payload=payload)
        ):
            self.assertEqual(self.graph.get_thumbnail_url("D", "I"), "https://t/large")
            self.assertEqual(self.graph.get_thumbnail_url("D", "I", size="small"), "s")
            self.assertFalse(self.graph.get_thumbnail_url("D", "I", size="medium"))
        with patch(
            CLIENT + ".requests.get", return_value=FakeResponse(payload={"value": []})
        ):
            self.assertFalse(self.graph.get_thumbnail_url("D", "I"))
        with patch(CLIENT + ".requests.get", return_value=FakeResponse(404)):
            self.assertFalse(self.graph.get_thumbnail_url("D", "I"))
