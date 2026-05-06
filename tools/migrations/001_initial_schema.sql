-- Kvitly v2 initial schema (multi-tenant SaaS on Supabase)
-- Run via tools/supabase_bootstrap.py against a fresh Supabase project.

-- ============================================================================
-- Extensions
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

-- ============================================================================
-- Enum types
-- ============================================================================
DO $$ BEGIN
    CREATE TYPE kvittering_status AS ENUM ('afventer', 'godkendt', 'udbetalt', 'afvist');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- ============================================================================
-- Foreninger (tenants)
-- ============================================================================
CREATE TABLE IF NOT EXISTS foreninger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    navn TEXT NOT NULL,
    auth_user_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE SET NULL,
    upload_token TEXT UNIQUE NOT NULL,
    upload_token_rotated_at TIMESTAMPTZ DEFAULT now(),
    upload_disabled BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_foreninger_upload_token ON foreninger(upload_token);
CREATE INDEX IF NOT EXISTS idx_foreninger_auth_user ON foreninger(auth_user_id);

-- ============================================================================
-- Invite codes (closed beta)
-- ============================================================================
CREATE TABLE IF NOT EXISTS invite_codes (
    code TEXT PRIMARY KEY,
    note TEXT,
    used_by_forening UUID REFERENCES foreninger(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    used_at TIMESTAMPTZ
);

-- ============================================================================
-- Categories (per forening)
-- ============================================================================
CREATE TABLE IF NOT EXISTS kategorier (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    forening_id UUID NOT NULL REFERENCES foreninger(id) ON DELETE CASCADE,
    navn TEXT NOT NULL,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(forening_id, navn)
);
CREATE INDEX IF NOT EXISTS idx_kategorier_forening ON kategorier(forening_id, sort_order);

-- ============================================================================
-- Udvalg (per forening)
-- ============================================================================
CREATE TABLE IF NOT EXISTS udvalg (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    forening_id UUID NOT NULL REFERENCES foreninger(id) ON DELETE CASCADE,
    navn TEXT NOT NULL,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(forening_id, navn)
);
CREATE INDEX IF NOT EXISTS idx_udvalg_forening ON udvalg(forening_id, sort_order);

-- ============================================================================
-- Budgetter (per udvalg × kategori × år)
-- ============================================================================
CREATE TABLE IF NOT EXISTS budgetter (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    forening_id UUID NOT NULL REFERENCES foreninger(id) ON DELETE CASCADE,
    udvalg TEXT,
    kategori TEXT,
    aar INT NOT NULL,
    beloeb NUMERIC(10,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(forening_id, udvalg, kategori, aar)
);
CREATE INDEX IF NOT EXISTS idx_budgetter_forening_aar ON budgetter(forening_id, aar);

-- ============================================================================
-- Kvitteringer
-- ============================================================================
CREATE TABLE IF NOT EXISTS kvitteringer (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    forening_id UUID NOT NULL REFERENCES foreninger(id) ON DELETE CASCADE,
    dato DATE,
    indsendt_at TIMESTAMPTZ DEFAULT now(),
    navn TEXT,
    submitter_email TEXT,
    type TEXT,
    udvalg TEXT,
    telefon TEXT,
    reg_nr TEXT,
    konto_nr TEXT,
    butik TEXT,
    beskrivelse TEXT,
    beloeb NUMERIC(10,2),
    valuta TEXT DEFAULT 'DKK',
    kategori TEXT,
    kommentar TEXT,
    admin_note TEXT,
    ocr_note TEXT,
    billede_path TEXT,
    status kvittering_status DEFAULT 'afventer',
    udbetalt_dato DATE,
    submitter_ip INET,
    last_modified_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    last_modified_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_kvit_forening_dato ON kvitteringer(forening_id, dato DESC);
CREATE INDEX IF NOT EXISTS idx_kvit_forening_status ON kvitteringer(forening_id, status);
CREATE INDEX IF NOT EXISTS idx_kvit_indsendt ON kvitteringer(forening_id, indsendt_at DESC);

-- ============================================================================
-- Auto-update timestamp trigger
-- ============================================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_kvitteringer_updated_at ON kvitteringer;
CREATE TRIGGER set_kvitteringer_updated_at
    BEFORE UPDATE ON kvitteringer
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================================
-- Row-Level Security
-- ============================================================================
ALTER TABLE foreninger ENABLE ROW LEVEL SECURITY;
ALTER TABLE kategorier ENABLE ROW LEVEL SECURITY;
ALTER TABLE udvalg ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgetter ENABLE ROW LEVEL SECURITY;
ALTER TABLE kvitteringer ENABLE ROW LEVEL SECURITY;
ALTER TABLE invite_codes ENABLE ROW LEVEL SECURITY;

-- Helper: get forening_id for current authenticated admin
CREATE OR REPLACE FUNCTION current_forening_id()
RETURNS UUID
LANGUAGE SQL
STABLE
AS $$
    SELECT id FROM foreninger WHERE auth_user_id = auth.uid()
$$;

-- foreninger: admin can read+update own row only
DROP POLICY IF EXISTS forening_self_select ON foreninger;
CREATE POLICY forening_self_select ON foreninger
    FOR SELECT TO authenticated
    USING (auth_user_id = auth.uid());

DROP POLICY IF EXISTS forening_self_update ON foreninger;
CREATE POLICY forening_self_update ON foreninger
    FOR UPDATE TO authenticated
    USING (auth_user_id = auth.uid());

-- kategorier: admin sees own forening's
DROP POLICY IF EXISTS kategorier_self ON kategorier;
CREATE POLICY kategorier_self ON kategorier
    FOR ALL TO authenticated
    USING (forening_id = current_forening_id())
    WITH CHECK (forening_id = current_forening_id());

-- udvalg: admin sees own forening's
DROP POLICY IF EXISTS udvalg_self ON udvalg;
CREATE POLICY udvalg_self ON udvalg
    FOR ALL TO authenticated
    USING (forening_id = current_forening_id())
    WITH CHECK (forening_id = current_forening_id());

-- budgetter: admin sees own forening's
DROP POLICY IF EXISTS budgetter_self ON budgetter;
CREATE POLICY budgetter_self ON budgetter
    FOR ALL TO authenticated
    USING (forening_id = current_forening_id())
    WITH CHECK (forening_id = current_forening_id());

-- kvitteringer: admin sees own forening's
DROP POLICY IF EXISTS kvitteringer_self ON kvitteringer;
CREATE POLICY kvitteringer_self ON kvitteringer
    FOR ALL TO authenticated
    USING (forening_id = current_forening_id())
    WITH CHECK (forening_id = current_forening_id());

-- invite_codes: admins cannot read (only service_role can manage these)
-- (no policy = no access for authenticated users; service_role bypasses RLS)
