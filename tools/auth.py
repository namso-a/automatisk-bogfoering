"""Auth helpers for Kvitly v2 — Supabase Auth integration via Flask cookies.

Flow:
    1. User POSTs email + password to /login
    2. Flask calls supabase.auth.sign_in_with_password (server-side)
    3. On success, Flask sets HTTP-only cookie "kvitly_jwt" with the access token
    4. Subsequent dashboard requests pass through @require_forening_admin
       which decodes + validates the JWT locally using the project's JWKS
       (asymmetric ES256 signing keys) and loads the forening into flask.g
"""

from __future__ import annotations

import os
from functools import wraps
from pathlib import Path

import jwt
from jwt import PyJWKClient
from dotenv import load_dotenv
from flask import g, jsonify, redirect, request, url_for
from supabase import Client, create_client

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
# Legacy fallback for projects still using HS256 shared-secret signing.
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

JWT_COOKIE_NAME = "kvitly_jwt"
JWT_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 dage

# JWKS client — fetches project's public signing keys, caches them.
_jwks_client: PyJWKClient | None = None


def jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not SUPABASE_URL:
            raise RuntimeError("SUPABASE_URL missing. Run tools/supabase_bootstrap.py.")
        _jwks_client = PyJWKClient(
            f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json",
            cache_keys=True,
            lifespan=3600,
        )
    return _jwks_client


_anon_client: Client | None = None


def anon_client() -> Client:
    """Client for end-user auth flows (sign in, sign up, password reset)."""
    global _anon_client
    if _anon_client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise RuntimeError(
                "SUPABASE_URL or SUPABASE_ANON_KEY missing. Run tools/supabase_bootstrap.py."
            )
        _anon_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _anon_client


# =============================================================================
# JWT decoding
# =============================================================================


def decode_jwt(token: str) -> dict | None:
    """Decode and validate a Supabase access token. Returns payload or None.

    Tries asymmetric (JWKS / ES256) first, falls back to legacy HS256 shared secret.
    """
    if not token:
        return None

    # Inspect header to determine algorithm
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        return None

    alg = header.get("alg", "")

    # Asymmetric algorithms (ES256, RS256) — fetch public key via JWKS
    if alg in ("ES256", "RS256", "EdDSA"):
        try:
            signing_key = jwks_client().get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience="authenticated",
            )
        except (jwt.PyJWTError, Exception):
            return None

    # Legacy HS256 with shared secret
    if alg == "HS256" and SUPABASE_JWT_SECRET:
        try:
            return jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except jwt.PyJWTError:
            return None

    return None


def get_jwt_from_request() -> str:
    """Look in Authorization header first, then cookie."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return request.cookies.get(JWT_COOKIE_NAME, "")


# =============================================================================
# Decorators
# =============================================================================


def require_forening_admin(f):
    """Require valid JWT → load forening into flask.g.forening + g.user_id."""
    from tools.db import forening_by_auth_user

    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_jwt_from_request()
        payload = decode_jwt(token)
        if not payload:
            if request.path.startswith("/dashboard/api/"):
                return jsonify({"error": "Ikke logget ind."}), 401
            return redirect(url_for("login"))

        user_id = payload.get("sub")
        if not user_id:
            return _unauth_response()

        forening = forening_by_auth_user(user_id)
        if not forening:
            # Authenticated but no forening linked → must complete signup
            return redirect(url_for("signup"))

        g.user_id = user_id
        g.user_email = payload.get("email")
        g.forening = forening
        return f(*args, **kwargs)

    return decorated


def _unauth_response():
    if request.path.startswith("/dashboard/api/"):
        return jsonify({"error": "Ikke logget ind."}), 401
    return redirect(url_for("login"))


# =============================================================================
# Helpers for routes
# =============================================================================


def set_jwt_cookie(response, jwt_token: str) -> None:
    """Set the auth cookie on a Flask response."""
    secure = os.environ.get("FLASK_ENV", "").lower() != "development"
    response.set_cookie(
        JWT_COOKIE_NAME,
        jwt_token,
        max_age=JWT_COOKIE_MAX_AGE,
        httponly=True,
        secure=secure,
        samesite="Lax",
    )


def clear_jwt_cookie(response) -> None:
    response.delete_cookie(JWT_COOKIE_NAME)


def sign_in_with_password(email: str, password: str) -> tuple[str | None, str | None]:
    """Server-side login. Returns (access_token, error_msg)."""
    try:
        sb = anon_client()
        result = sb.auth.sign_in_with_password({"email": email, "password": password})
        if result.session and result.session.access_token:
            return result.session.access_token, None
        return None, "Login mislykkedes."
    except Exception as e:
        return None, str(e)


def sign_up_with_password(email: str, password: str) -> tuple[str | None, str | None, str | None]:
    """Server-side signup. Returns (user_id, access_token, error_msg).

    Note: Supabase may require email confirmation; in that case access_token
    will be None and caller should ask user to verify their email.
    """
    try:
        sb = anon_client()
        result = sb.auth.sign_up({"email": email, "password": password})
        if not result.user:
            return None, None, "Kunne ikke oprette bruger."
        user_id = result.user.id
        access_token = result.session.access_token if result.session else None
        return user_id, access_token, None
    except Exception as e:
        return None, None, str(e)
