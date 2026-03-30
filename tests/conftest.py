import os

# Set dummy env vars before any module imports config() at module level
os.environ.setdefault("TWILIO_ACCOUNT_SID", "test_sid")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test_token")
os.environ.setdefault("TWILIO_NUMBER", "test_number")
os.environ.setdefault("TWILIO_WHATSAPP_NUMBER", "test_wa_number")
os.environ.setdefault("TWILIO_MESSAGING_SERVICE_SID", "test_mg_sid")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test_key")
