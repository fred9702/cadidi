-- Create conversation session table for multi-turn WhatsApp AI interactions.

CREATE TABLE wa_conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_hash text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    last_message_at timestamptz NOT NULL DEFAULT now(),
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'expired')),
    language text NOT NULL DEFAULT 'fr'
);

CREATE INDEX idx_wa_conversations_phone_hash
ON wa_conversations (phone_hash);

CREATE INDEX idx_wa_conversations_active_lookup
ON wa_conversations (phone_hash, status);
