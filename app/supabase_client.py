from supabase import create_client, Client
from decouple import config


def get_supabase() -> Client:
    """Create and return a Supabase client."""
    return create_client(
        config("SUPABASE_URL"),
        config("SUPABASE_KEY"),
    )
