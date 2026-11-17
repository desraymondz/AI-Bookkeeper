from typing import Any

from authlib.integrations.starlette_client import OAuth  # type: ignore[import-untyped]
from fastapi import Request

from bookkeeper.config import Settings

GOOGLE_METADATA_URL = "https://accounts.google.com/.well-known/openid-configuration"


def build_google_client(settings: Settings) -> Any:
    """See planning/03-tech-stack.md section 3.2 (Authlib row)."""
    oauth = OAuth()
    return oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url=GOOGLE_METADATA_URL,
        client_kwargs={"scope": "openid email profile"},
    )


def get_google_client(request: Request) -> Any:
    return request.app.state.google_oauth
