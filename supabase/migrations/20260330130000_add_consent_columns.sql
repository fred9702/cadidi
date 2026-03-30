-- Add WhatsApp opt-in consent tracking columns to registrations table.

-- Consent status for WhatsApp AI assistant (separate from gdpr_consent which covers registration)
ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS consent_status text NOT NULL DEFAULT 'registered'
    CHECK (consent_status IN ('registered', 'active', 'opted_out'));

ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS consent_given_at timestamptz;

ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS consent_revoked_at timestamptz;

-- SHA-256 hash of phone number for RGPD-compliant webhook lookups
ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS phone_hash text;

-- Index for fast webhook lookups on every incoming message
CREATE INDEX IF NOT EXISTS idx_registrations_phone_hash
ON registrations (phone_hash);

-- Backfill phone_hash from existing raw phone numbers
UPDATE registrations
SET phone_hash = encode(sha256(phone::bytea), 'hex')
WHERE phone_hash IS NULL AND phone IS NOT NULL;
