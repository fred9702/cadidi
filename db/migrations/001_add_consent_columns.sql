-- Add consent tracking columns to the registration table.
-- Run this in the Supabase SQL Editor.

ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS consent_status text NOT NULL DEFAULT 'registered'
    CHECK (consent_status IN ('registered', 'active', 'opted_out'));

ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS consent_given_at timestamptz;

ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS consent_revoked_at timestamptz;

-- Add phone_hash column if it doesn't already exist.
-- If your registration table already stores phone hashes, skip this.
ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS phone_hash text;

-- Index for fast webhook lookups
CREATE INDEX IF NOT EXISTS idx_registrations_phone_hash
ON registrations (phone_hash);

-- Backfill phone_hash for existing rows (if raw phone numbers exist).
-- Replace 'phone_number' with the actual column name holding raw numbers.
-- Run this ONCE then remove raw phone numbers for RGPD compliance.
--
-- UPDATE registrations
-- SET phone_hash = encode(sha256(phone_number::bytea), 'hex')
-- WHERE phone_hash IS NULL AND phone_number IS NOT NULL;
