"""Supabase client wrapper for Kvitly v2.

Provides helpers Flask uses to read/write data with the service_role key.
Service-role bypasses RLS, so all RLS-policy enforcement happens client-side
via current-user-context decorators in tools/auth.py and explicit forening_id
filters here.
"""

from __future__ import annotations

import os
import secrets
import string
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
STORAGE_BUCKET = "kvitteringer"

_client: Client | None = None


def service_client() -> Client:
    """Return a singleton Supabase client using the service_role key."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise RuntimeError(
                "SUPABASE_URL or SUPABASE_SERVICE_KEY missing in .env. "
                "Run tools/supabase_bootstrap.py first."
            )
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client


# =============================================================================
# Token generation
# =============================================================================

UPLOAD_TOKEN_ALPHABET = string.ascii_lowercase + string.digits  # 36 chars
UPLOAD_TOKEN_LENGTH = 8


def gen_upload_token() -> str:
    return "".join(secrets.choice(UPLOAD_TOKEN_ALPHABET) for _ in range(UPLOAD_TOKEN_LENGTH))


def gen_invite_code() -> str:
    return gen_upload_token()  # same format


# =============================================================================
# Foreninger
# =============================================================================


def forening_by_token(token: str) -> dict | None:
    """Lookup forening by upload-token. Returns None if not found or disabled."""
    if not token or len(token) != UPLOAD_TOKEN_LENGTH:
        return None
    sb = service_client()
    res = (
        sb.table("foreninger")
        .select("*")
        .eq("upload_token", token)
        .eq("upload_disabled", False)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def forening_by_auth_user(auth_user_id: str) -> dict | None:
    sb = service_client()
    res = (
        sb.table("foreninger")
        .select("*")
        .eq("auth_user_id", auth_user_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def forening_by_id(forening_id: str) -> dict | None:
    sb = service_client()
    res = sb.table("foreninger").select("*").eq("id", forening_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def create_forening(slug: str, navn: str, auth_user_id: str) -> dict:
    """Create a new forening for a freshly-signed-up admin."""
    sb = service_client()
    # Ensure unique upload_token (collision-resistant; loop max 5x)
    for _ in range(5):
        token = gen_upload_token()
        existing = (
            sb.table("foreninger").select("id").eq("upload_token", token).limit(1).execute()
        )
        if not existing.data:
            break
    else:
        raise RuntimeError("Could not generate unique upload_token after 5 tries")

    res = (
        sb.table("foreninger")
        .insert(
            {
                "slug": slug,
                "navn": navn,
                "auth_user_id": auth_user_id,
                "upload_token": token,
            }
        )
        .execute()
    )
    return res.data[0]


def regenerate_upload_token(forening_id: str) -> str:
    sb = service_client()
    for _ in range(5):
        token = gen_upload_token()
        existing = (
            sb.table("foreninger").select("id").eq("upload_token", token).limit(1).execute()
        )
        if not existing.data:
            break
    else:
        raise RuntimeError("Could not generate unique upload_token after 5 tries")

    sb.table("foreninger").update(
        {
            "upload_token": token,
            "upload_token_rotated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", forening_id).execute()
    return token


def set_upload_disabled(forening_id: str, disabled: bool) -> None:
    service_client().table("foreninger").update({"upload_disabled": disabled}).eq(
        "id", forening_id
    ).execute()


# =============================================================================
# Invite codes
# =============================================================================


def find_invite_code(code: str) -> dict | None:
    if not code:
        return None
    sb = service_client()
    res = (
        sb.table("invite_codes")
        .select("*")
        .eq("code", code.lower().strip())
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def consume_invite_code(code: str, forening_id: str) -> bool:
    """Mark invite-code as used. Returns True on success, False if already used."""
    sb = service_client()
    invite = find_invite_code(code)
    if not invite or invite.get("used_at"):
        return False
    sb.table("invite_codes").update(
        {
            "used_by_forening": forening_id,
            "used_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("code", invite["code"]).execute()
    return True


def create_invite_code(note: str = "") -> str:
    sb = service_client()
    for _ in range(5):
        code = gen_invite_code()
        existing = sb.table("invite_codes").select("code").eq("code", code).limit(1).execute()
        if not existing.data:
            sb.table("invite_codes").insert({"code": code, "note": note}).execute()
            return code
    raise RuntimeError("Could not generate unique invite code after 5 tries")


# =============================================================================
# Storage
# =============================================================================


def upload_image(forening_slug: str, file_bytes: bytes, ext: str) -> str:
    """Upload image to Storage. Returns the storage path (relative to bucket)."""
    ext = (ext or ".jpg").lstrip(".").lower()
    if ext not in {"jpg", "jpeg", "png", "webp", "gif", "heic"}:
        ext = "jpg"
    now = datetime.now(timezone.utc)
    path = f"{forening_slug}/{now.year}/{now.month:02d}/{uuid.uuid4().hex}.{ext}"

    mime_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
        "heic": "image/heic",
    }
    sb = service_client()
    sb.storage.from_(STORAGE_BUCKET).upload(
        path,
        file_bytes,
        file_options={"content-type": mime_map.get(ext, "image/jpeg")},
    )
    return path


def public_image_url(path: str) -> str:
    if not path:
        return ""
    return f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{path}"


def delete_image(path: str) -> None:
    if not path:
        return
    try:
        service_client().storage.from_(STORAGE_BUCKET).remove([path])
    except Exception:
        pass


# =============================================================================
# Kvitteringer
# =============================================================================


def insert_kvittering(forening_id: str, data: dict[str, Any]) -> dict:
    """Insert a new kvittering row. Caller has already uploaded image and put path in data['billede_path']."""
    payload = {"forening_id": forening_id, **data}
    res = service_client().table("kvitteringer").insert(payload).execute()
    return res.data[0]


def list_kvitteringer(forening_id: str, limit: int = 1000) -> list[dict]:
    sb = service_client()
    res = (
        sb.table("kvitteringer")
        .select("*")
        .eq("forening_id", forening_id)
        .order("indsendt_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def get_kvittering(kvittering_id: str, forening_id: str) -> dict | None:
    sb = service_client()
    res = (
        sb.table("kvitteringer")
        .select("*")
        .eq("id", kvittering_id)
        .eq("forening_id", forening_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def update_kvittering(
    kvittering_id: str,
    forening_id: str,
    updates: dict[str, Any],
    actor_user_id: str | None = None,
) -> dict | None:
    """Update kvittering, scoped to forening for safety. Stamps last_modified_*."""
    sb = service_client()
    payload = dict(updates)
    if actor_user_id:
        payload["last_modified_by"] = actor_user_id
    payload["last_modified_at"] = datetime.now(timezone.utc).isoformat()

    res = (
        sb.table("kvitteringer")
        .update(payload)
        .eq("id", kvittering_id)
        .eq("forening_id", forening_id)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def delete_kvittering(kvittering_id: str, forening_id: str) -> bool:
    sb = service_client()
    row = get_kvittering(kvittering_id, forening_id)
    if not row:
        return False
    if row.get("billede_path"):
        delete_image(row["billede_path"])
    sb.table("kvitteringer").delete().eq("id", kvittering_id).eq(
        "forening_id", forening_id
    ).execute()
    return True


# =============================================================================
# Categories / Udvalg / Budgets
# =============================================================================


def list_categories(forening_id: str) -> list[dict]:
    sb = service_client()
    res = (
        sb.table("kategorier")
        .select("*")
        .eq("forening_id", forening_id)
        .order("sort_order")
        .order("navn")
        .execute()
    )
    return res.data or []


def add_category(forening_id: str, navn: str) -> dict:
    sb = service_client()
    res = (
        sb.table("kategorier")
        .insert({"forening_id": forening_id, "navn": navn})
        .execute()
    )
    return res.data[0]


def delete_category(forening_id: str, category_id: str) -> None:
    service_client().table("kategorier").delete().eq("id", category_id).eq(
        "forening_id", forening_id
    ).execute()


def list_udvalg(forening_id: str) -> list[dict]:
    sb = service_client()
    res = (
        sb.table("udvalg")
        .select("*")
        .eq("forening_id", forening_id)
        .order("sort_order")
        .order("navn")
        .execute()
    )
    return res.data or []


def add_udvalg(forening_id: str, navn: str) -> dict:
    sb = service_client()
    res = (
        sb.table("udvalg").insert({"forening_id": forening_id, "navn": navn}).execute()
    )
    return res.data[0]


def delete_udvalg(forening_id: str, udvalg_id: str) -> None:
    service_client().table("udvalg").delete().eq("id", udvalg_id).eq(
        "forening_id", forening_id
    ).execute()


def list_budgets(forening_id: str, aar: int | None = None) -> list[dict]:
    sb = service_client()
    q = sb.table("budgetter").select("*").eq("forening_id", forening_id)
    if aar is not None:
        q = q.eq("aar", aar)
    res = q.order("aar", desc=True).execute()
    return res.data or []


def upsert_budget(
    forening_id: str, aar: int, beloeb: float, udvalg: str | None = None, kategori: str | None = None
) -> dict:
    sb = service_client()
    res = (
        sb.table("budgetter")
        .upsert(
            {
                "forening_id": forening_id,
                "udvalg": udvalg,
                "kategori": kategori,
                "aar": aar,
                "beloeb": beloeb,
            },
            on_conflict="forening_id,udvalg,kategori,aar",
        )
        .execute()
    )
    return res.data[0]
