"""
Admin endpoints — usage analytics and user drill-down.
All routes require a valid JWT with is_admin=True.
"""

from fastapi import APIRouter, Cookie, HTTPException

from app.core.config import get_settings
from app.services.auth import COOKIE_NAME, decode_jwt
from app.services.usage_tracker import get_usage_tracker

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


def _require_admin(ecc_token: str | None) -> None:
    if not ecc_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token_data = decode_jwt(settings, ecc_token)
    if not token_data or not token_data.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/stats")
async def admin_stats(ecc_token: str | None = Cookie(default=None)) -> dict:
    """Overall platform growth metrics."""
    _require_admin(ecc_token)
    tracker = get_usage_tracker(settings.usage_db_path)
    return tracker.overall_stats()


@router.get("/users")
async def admin_users(ecc_token: str | None = Cookie(default=None)) -> list[dict]:
    """All users with usage summary sorted by last active."""
    _require_admin(ecc_token)
    tracker = get_usage_tracker(settings.usage_db_path)
    return tracker.users_summary()


@router.get("/users/{email:path}")
async def admin_user_detail(
    email: str,
    ecc_token: str | None = Cookie(default=None),
) -> dict:
    """Per-user query history and daily activity."""
    _require_admin(ecc_token)
    tracker = get_usage_tracker(settings.usage_db_path)
    return {
        "queries": tracker.user_queries(email),
        "daily_activity": tracker.user_daily_activity(email),
    }
