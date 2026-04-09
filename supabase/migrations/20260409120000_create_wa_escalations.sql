-- Create escalation tracking table for human handoff.

CREATE TABLE wa_escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES wa_conversations(id),
    phone_hash TEXT NOT NULL,
    reason TEXT,
    user_message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_escalations_phone_status ON wa_escalations(phone_hash, status);
