"""Official Meta Graph API client for Facebook Page photo publishing.

Only the documented ``/{page-id}/photos`` endpoint is used. The access token is
sent in the request body (as Meta requires) and is never logged, stored in the
database or rendered in the dashboard.
"""

from __future__ import annotations

from pathlib import Path

import requests

GRAPH_BASE = "https://graph.facebook.com"


class FacebookError(RuntimeError):
    """Raised for configuration or Graph API failures."""


class FacebookGraphClient:
    def __init__(self, settings, session: requests.Session | None = None) -> None:
        self.settings = settings
        self.session = session or requests.Session()

    # -- helpers ---------------------------------------------------------
    @property
    def base_url(self) -> str:
        return f"{GRAPH_BASE}/{self.settings.graph_api_version}"

    def _require_credentials(self) -> None:
        missing = self.settings.facebook_missing
        if missing:
            raise FacebookError(
                "Facebook Page credentials are missing: "
                + ", ".join(missing)
                + ". Set them as environment variables."
            )

    def _redact(self, text: str) -> str:
        token = self.settings.fb_page_access_token
        if token:
            text = text.replace(token, "***")
        return text[:500]

    def _handle(self, response: requests.Response) -> dict:
        try:
            payload = response.json()
        except ValueError:
            raise FacebookError(f"Graph API returned HTTP {response.status_code} with no JSON body.") from None

        if response.status_code >= 400 or "error" in payload:
            error = payload.get("error") or {}
            message = error.get("message") or f"HTTP {response.status_code}"
            code = error.get("code", response.status_code)
            raise FacebookError(self._redact(f"Graph API error {code}: {message}"))
        return payload

    # -- API calls -------------------------------------------------------
    def verify_page(self) -> dict:
        """Confirm the token can read the configured Page."""
        self._require_credentials()
        url = f"{self.base_url}/{self.settings.fb_page_id}"
        params = {
            "fields": "id,name,link",
            "access_token": self.settings.fb_page_access_token,
        }
        try:
            response = self.session.get(url, params=params, timeout=30)
        except requests.RequestException as exc:
            raise FacebookError(f"Could not reach the Graph API: {exc.__class__.__name__}") from exc
        payload = self._handle(response)
        return {"id": payload.get("id"), "name": payload.get("name"), "link": payload.get("link", "")}

    def publish_photo(self, image_path: str | Path, message: str) -> dict:
        """Upload a photo to the Page feed. Returns the photo id and permalink."""
        self._require_credentials()
        path = Path(image_path)
        if not path.exists():
            raise FacebookError(f"Image file is missing: {path.name}")

        url = f"{self.base_url}/{self.settings.fb_page_id}/photos"
        data = {
            "message": message,
            "published": "true",
            "access_token": self.settings.fb_page_access_token,
        }
        try:
            with path.open("rb") as handle:
                files = {"source": (path.name, handle, "image/jpeg")}
                response = self.session.post(url, data=data, files=files, timeout=120)
        except requests.RequestException as exc:
            raise FacebookError(f"Could not reach the Graph API: {exc.__class__.__name__}") from exc

        payload = self._handle(response)
        photo_id = payload.get("id") or payload.get("post_id") or ""
        return {
            "photo_id": photo_id,
            "permalink": f"https://www.facebook.com/{photo_id}" if photo_id else "",
            "payload": payload,
        }

    def build_photo_request(self, image_path: str | Path, message: str) -> dict:
        """Describe the exact upload request without sending it.

        Used by dry-run mode so the integration can be verified without
        publishing a real post.
        """
        self._require_credentials()
        path = Path(image_path)
        if not path.exists():
            raise FacebookError(f"Image file is missing: {path.name}")
        return {
            "method": "POST",
            "url": f"{self.base_url}/{self.settings.fb_page_id}/photos",
            "fields": {
                "message": message,
                "published": "true",
                "access_token": "<redacted>",
            },
            "file": {
                "field": "source",
                "name": path.name,
                "mime": "image/jpeg",
                "bytes": path.stat().st_size,
            },
        }

    def dry_run_publish(self, image_path: str | Path, message: str) -> dict:
        """Validate a publish locally. Never contacts Facebook."""
        request = self.build_photo_request(image_path, message)
        return {
            "dry_run": True,
            "sent": False,
            "request": request,
            "checks": {
                "credentials_present": bool(
                    self.settings.fb_page_id and self.settings.fb_page_access_token
                ),
                "image_exists": Path(image_path).exists(),
                "image_not_empty": request["file"]["bytes"] > 0,
                "message_not_empty": bool(message.strip()),
                "message_within_limit": len(message) <= 63_206,
            },
        }
