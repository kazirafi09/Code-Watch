from __future__ import annotations

import contextlib
import logging
import os
import secrets
from pathlib import Path

from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)

# Default token location: per-user dotfile so multiple users on the same host
# can't read each other's tokens. Override with CODEWATCH_TOKEN_PATH for tests.
_TOKEN_DIR = Path.home() / ".codewatch"
_TOKEN_FILE_DEFAULT = _TOKEN_DIR / "token"

# Opt-in. The primary defense is `--host 127.0.0.1` (set in start.sh/start.bat).
# Token auth is a second layer for users who bind 0.0.0.0 intentionally (LAN
# dev, Docker bind-mount, WSL, etc.). When disabled, the dependency no-ops.
_AUTH_ENABLED_ENV = "CODEWATCH_REQUIRE_TOKEN"


def _token_path() -> Path:
    override = os.environ.get("CODEWATCH_TOKEN_PATH")
    if override:
        return Path(override)
    return _TOKEN_FILE_DEFAULT


def is_auth_enabled() -> bool:
    return os.environ.get(_AUTH_ENABLED_ENV) == "1"


def get_or_create_token() -> str:
    """Return the current API token, minting one on first call.

    The file is created with 0600 permissions on POSIX. On Windows, filesystem
    ACLs already restrict home-directory files to the owning user, so we
    don't bother with explicit chmod.
    """
    path = _token_path()
    if path.exists():
        try:
            token = path.read_text(encoding="utf-8").strip()
            if token:
                return token
        except OSError as exc:
            logger.warning("Cannot read token file %s: %s", path, exc)

    token = secrets.token_urlsafe(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token, encoding="utf-8")
    # Best-effort on POSIX; a no-op with a harmless error on Windows.
    with contextlib.suppress(OSError):
        os.chmod(path, 0o600)
    logger.info("Generated new API token at %s", path)
    return token


async def require_token(authorization: str | None = Header(default=None)) -> None:
    """FastAPI dependency enforcing Bearer-token auth.

    No-ops when CODEWATCH_REQUIRE_TOKEN is not set, so the default local
    workflow (loopback bind, single user) keeps working without configuration.
    """
    if not is_auth_enabled():
        return
    expected = get_or_create_token()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    provided = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def check_ws_token(token: str | None) -> bool:
    """True if the provided query-string token is valid (or auth is disabled)."""
    if not is_auth_enabled():
        return True
    if not token:
        return False
    expected = get_or_create_token()
    return secrets.compare_digest(token, expected)
