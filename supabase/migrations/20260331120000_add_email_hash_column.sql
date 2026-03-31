-- Add email_hash column for email-based consent lookups.
-- Used when a registrant has no phone number and identifies via email in WhatsApp.

ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS email_hash text;

CREATE INDEX IF NOT EXISTS idx_registrations_email_hash
ON registrations (email_hash);

-- Backfill from existing email column
UPDATE registrations
SET email_hash = encode(sha256(lower(trim(email))::bytea), 'hex')
WHERE email_hash IS NULL AND email IS NOT NULL;
