"""Bootstrap a Supabase project for Kvitly v2.

One-time setup script. Requires SUPABASE_PAT (Personal Access Token) in .env.
Generate one at: https://supabase.com/dashboard/account/tokens

Steps:
    1. Verify PAT works (list orgs, pick one)
    2. Create project "kvitly" in EU-region (or use existing if --use-existing <ref>)
    3. Wait for project to be ACTIVE_HEALTHY
    4. Fetch service_role + anon keys via Management API
    5. Run schema migration (tools/migrations/001_initial_schema.sql)
    6. Create storage bucket "kvitteringer" (public read)
    7. Generate seed invite-code for first forening (Oliven Spejderne)
    8. Write SUPABASE_URL/SERVICE_KEY/ANON_KEY/JWT_SECRET to .env

Usage:
    python tools/supabase_bootstrap.py
    python tools/supabase_bootstrap.py --use-existing <project_ref>
    python tools/supabase_bootstrap.py --schema-only --project-ref <ref>  # re-run migration only
"""

from __future__ import annotations

import argparse
import os
import secrets
import string
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
MIGRATION_PATH = ROOT / "tools" / "migrations" / "001_initial_schema.sql"

MGMT_BASE = "https://api.supabase.com/v1"
PROJECT_NAME = "kvitly"
DB_REGION = "eu-central-1"  # Frankfurt
STORAGE_BUCKET = "kvitteringer"


def load_pat() -> str:
    load_dotenv(ENV_PATH)
    pat = os.environ.get("SUPABASE_PAT", "").strip()
    if not pat:
        sys.exit(
            "[error] SUPABASE_PAT not in .env.\n"
            "Generate one at: https://supabase.com/dashboard/account/tokens\n"
            "Then add to .env: SUPABASE_PAT=sbp_..."
        )
    return pat


def mgmt_headers(pat: str) -> dict:
    return {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}


def list_organizations(pat: str) -> list[dict]:
    r = requests.get(f"{MGMT_BASE}/organizations", headers=mgmt_headers(pat), timeout=30)
    r.raise_for_status()
    return r.json()


def list_projects(pat: str) -> list[dict]:
    r = requests.get(f"{MGMT_BASE}/projects", headers=mgmt_headers(pat), timeout=30)
    r.raise_for_status()
    return r.json()


def find_existing_project(pat: str, name: str) -> dict | None:
    for p in list_projects(pat):
        if p.get("name") == name:
            return p
    return None


def gen_db_password(n: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def create_project(pat: str, org_id: str) -> dict:
    db_password = gen_db_password()
    payload = {
        "name": PROJECT_NAME,
        "organization_id": org_id,
        "region": DB_REGION,
        "db_pass": db_password,
        "plan": "free",
    }
    print(f"[info] Creating project '{PROJECT_NAME}' in org {org_id} (region {DB_REGION})...")
    r = requests.post(f"{MGMT_BASE}/projects", headers=mgmt_headers(pat), json=payload, timeout=60)
    if r.status_code >= 400:
        sys.exit(f"[error] Project creation failed ({r.status_code}): {r.text}")
    project = r.json()
    project["_db_password"] = db_password
    return project


def wait_active(pat: str, project_ref: str, timeout_s: int = 300) -> dict:
    start = time.monotonic()
    last_status = None
    while time.monotonic() - start < timeout_s:
        r = requests.get(f"{MGMT_BASE}/projects/{project_ref}", headers=mgmt_headers(pat), timeout=30)
        if r.status_code == 200:
            data = r.json()
            status = data.get("status")
            if status != last_status:
                print(f"[info] Project status: {status}")
                last_status = status
            if status == "ACTIVE_HEALTHY":
                return data
            if status in ("INIT_FAILED", "FAILED"):
                sys.exit(f"[error] Project failed to provision: {status}")
        time.sleep(5)
    sys.exit(f"[error] Timed out waiting for project to become ACTIVE_HEALTHY after {timeout_s}s")


def fetch_keys(pat: str, project_ref: str) -> dict:
    """Fetch service_role + anon API keys."""
    r = requests.get(
        f"{MGMT_BASE}/projects/{project_ref}/api-keys",
        headers=mgmt_headers(pat),
        timeout=30,
    )
    r.raise_for_status()
    keys = {k["name"]: k["api_key"] for k in r.json()}
    return {
        "anon": keys.get("anon", ""),
        "service_role": keys.get("service_role", ""),
    }


def fetch_jwt_secret(pat: str, project_ref: str) -> str:
    r = requests.get(
        f"{MGMT_BASE}/projects/{project_ref}/config/auth",
        headers=mgmt_headers(pat),
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("jwt_secret", "")


def run_sql(pat: str, project_ref: str, sql: str) -> None:
    """Execute SQL via Management API's database query endpoint."""
    print(f"[info] Running migration ({len(sql)} chars)...")
    r = requests.post(
        f"{MGMT_BASE}/projects/{project_ref}/database/query",
        headers=mgmt_headers(pat),
        json={"query": sql},
        timeout=120,
    )
    if r.status_code >= 400:
        sys.exit(f"[error] SQL execution failed ({r.status_code}): {r.text}")
    print("[info] Migration applied successfully.")


def create_storage_bucket(project_url: str, service_key: str, bucket: str) -> None:
    """Create public storage bucket via Storage REST API."""
    headers = {
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "apikey": service_key,
    }
    r = requests.post(
        f"{project_url}/storage/v1/bucket",
        headers=headers,
        json={"id": bucket, "name": bucket, "public": True},
        timeout=30,
    )
    if r.status_code == 200 or r.status_code == 201:
        print(f"[info] Storage bucket '{bucket}' created (public read).")
    elif r.status_code == 409 or "already exists" in r.text.lower():
        print(f"[info] Storage bucket '{bucket}' already exists, skipping.")
    else:
        sys.exit(f"[error] Bucket creation failed ({r.status_code}): {r.text}")


def gen_invite_code() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def seed_invite_code(project_url: str, service_key: str, note: str = "First-batch invite") -> str:
    code = gen_invite_code()
    headers = {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    r = requests.post(
        f"{project_url}/rest/v1/invite_codes",
        headers=headers,
        json={"code": code, "note": note},
        timeout=30,
    )
    if r.status_code >= 400:
        print(f"[warn] Could not seed invite code: {r.status_code} {r.text}")
        return ""
    print(f"[info] Seeded invite-code: {code}  ({note})")
    return code


def write_env(values: dict[str, str]) -> None:
    if not ENV_PATH.exists():
        ENV_PATH.touch()
    for k, v in values.items():
        set_key(str(ENV_PATH), k, v)
    print(f"[info] Wrote {len(values)} keys to .env")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--use-existing", metavar="REF", help="Use existing project ref instead of creating")
    parser.add_argument("--schema-only", action="store_true", help="Only run the SQL migration")
    parser.add_argument("--project-ref", help="Project ref (required with --schema-only)")
    args = parser.parse_args()

    pat = load_pat()

    # --schema-only branch: re-run migration on an existing project
    if args.schema_only:
        ref = args.project_ref or os.environ.get("SUPABASE_PROJECT_REF", "")
        if not ref:
            sys.exit("[error] --schema-only requires --project-ref or SUPABASE_PROJECT_REF in .env")
        sql = MIGRATION_PATH.read_text(encoding="utf-8")
        run_sql(pat, ref, sql)
        return 0

    # Determine project (existing or new)
    if args.use_existing:
        ref = args.use_existing
        print(f"[info] Using existing project ref: {ref}")
        project = wait_active(pat, ref)
    else:
        existing = find_existing_project(pat, PROJECT_NAME)
        if existing:
            ref = existing["id"]
            print(f"[info] Found existing project '{PROJECT_NAME}' (ref={ref}); reusing.")
            project = wait_active(pat, ref)
        else:
            orgs = list_organizations(pat)
            if not orgs:
                sys.exit("[error] No organizations found for this PAT.")
            org_id = orgs[0]["id"]
            print(f"[info] Using organization: {orgs[0]['name']} ({org_id})")
            project = create_project(pat, org_id)
            ref = project["id"]
            project = wait_active(pat, ref)

    project_url = f"https://{ref}.supabase.co"
    print(f"[info] Project URL: {project_url}")

    # Fetch keys
    keys = fetch_keys(pat, ref)
    if not keys["service_role"] or not keys["anon"]:
        sys.exit("[error] Could not fetch API keys.")
    jwt_secret = fetch_jwt_secret(pat, ref)

    # Run schema migration
    if not MIGRATION_PATH.exists():
        sys.exit(f"[error] Migration file missing: {MIGRATION_PATH}")
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    run_sql(pat, ref, sql)

    # Create storage bucket
    create_storage_bucket(project_url, keys["service_role"], STORAGE_BUCKET)

    # Seed first invite code
    seed_invite_code(project_url, keys["service_role"], note="Oliven Spejderne (first beta)")

    # Persist to .env
    env_values = {
        "SUPABASE_URL": project_url,
        "SUPABASE_PROJECT_REF": ref,
        "SUPABASE_ANON_KEY": keys["anon"],
        "SUPABASE_SERVICE_KEY": keys["service_role"],
        "SUPABASE_JWT_SECRET": jwt_secret,
    }
    write_env(env_values)

    print()
    print("=" * 60)
    print("[done] Supabase bootstrap complete.")
    print(f"  Project:  {project_url}")
    print(f"  Studio:   https://supabase.com/dashboard/project/{ref}")
    print("  Keys saved in .env (SUPABASE_*).")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
