"""Pydantic models for Google Health API request/response payloads."""

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, field_validator


class OAuthFlowState(BaseModel):
    """Per-request state stashed in the Django session between ``connect`` and ``callback``.

    ``state`` defends against CSRF; ``code_verifier`` completes the PKCE handshake
    after the user returns from Google's consent screen.
    """

    state: str
    code_verifier: str | None = None
    scopes: list[str]


class GoogleTokens(BaseModel):
    """Token-endpoint response from ``https://oauth2.googleapis.com/token``.

    Mirrors the JSON Google returns for both ``authorization_code`` and
    ``refresh_token`` grants. ``refresh_token`` is omitted on a refresh response,
    so it's optional.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    access_token: str
    expires_in: int
    token_type: str = "Bearer"
    scope: str = ""
    refresh_token: str | None = None
    refresh_token_expires_in: int | None = None
    id_token: str | None = None

    @field_validator("scope", mode="before")
    @classmethod
    def _coerce_scope(cls, value: object) -> str:
        # Google's raw token response uses a space-separated string; oauthlib parses
        # it into list[str] before returning. Accept both.
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return " ".join(str(v) for v in value)
        return str(value)

    @property
    def scopes(self) -> list[str]:
        return self.scope.split() if self.scope else []

    def expires_at(self, *, now: datetime | None = None) -> datetime:
        anchor = now or datetime.now(timezone.utc)
        return anchor + timedelta(seconds=self.expires_in)
